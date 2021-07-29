import copy, threading

DEFAULT_VERBOSITY = 0

class LockstepParallelDriver(object):
    """Facilitates a parallel programming structure with driver and worker threads.

    The processing occurs on a timestep clock. For each timestep,
    the driver thread prepares the data for the next timestep, while
    the workers process that data. Barriers are used to synchronize all
    threads at the end of each timestep.

    Parameters
    ----------
    nthreads : int
        Number of worker threads to create
    verbosity : int
        Level of verbosity, with 0 (silent), 1 (progress), 2+ (debugging)
    """
    def __init__(self, nthreads, verbosity=DEFAULT_VERBOSITY):
        self.nthreads = nthreads
        self.verbosity = verbosity
        self.barrier = threading.Barrier(nthreads + 1, timeout=threading.TIMEOUT_MAX)

        # Read-only, except update during intermission
        self.outputs = None

    def loop(self, start, *args, **kwargs):
        self.outputs = self._prepare_next()
        # Start all threads
        for proc in range(self.nthreads):
            thread = threading.Thread(None, start, args=tuple([proc, self] + list(args)), kwargs=kwargs)
            thread.start()
            
        # Initiate lockstep process
        while True:
            next_outputs = self._prepare_next()
            if not next_outputs:
                break
            
            # Barrier 1 is when everyone is done processing
            try:
                self.barrier.wait()
                self._intermission_threadsafe(next_outputs)
                if self.verbosity > 0:
                    print("----- LOCKSTEP -----")
                self.barrier.wait()
            except threading.BrokenBarrierError:
                # This happens if aborted while in prepare_next
                break

        try:
            self.barrier.wait()
            self.outputs = None # report that there's no more data
            self.barrier.wait()
        except threading.BrokenBarrierError:
            # This happens if aborted while in prepare_next
            pass

    def _intermission_threadsafe(self, next_outputs):
        # Everyone else immediately waits at barrier 2 for the data to be copied over
        self.outputs = next_outputs
        
    def _prepare_next(self):
        raise NotImplementedError

    def lockstep_pause(self):
        self.barrier.wait()
        self.barrier.wait()

class SharingLockstepParallelDriver(LockstepParallelDriver):
    """Lockstep system that introduces a Driver-level lock.

    This is used to sandbox worker threads, so that exceptions can be reported up to the driver.
    """
    def __init__(self, nthreads, verbosity=DEFAULT_VERBOSITY):
        super().__init__(nthreads, verbosity=verbosity)
        self.lock = threading.Lock() # for accessing driver-level attributes
        self.worker_exception = None
        self.workers_failed = 0

    def loop(self, start, *args, **kwargs):
        self.worker_exception = None
        self.workers_failed = 0
        super().loop(SharingLockstepParallelDriver._worker_sandbox, start, *args, **kwargs)

    def _intermission_threadsafe(self, next_outputs):
        # Check if all threads have failed
        if self.workers_failed == self.nthreads:
            print("All threads have failed.")
            raise self.worker_exception
        
        super()._intermission_threadsafe(next_outputs)

    @staticmethod
    def _worker_sandbox(proc, driver, start, *args, **kwargs):
        try:
            start(proc, driver, *args, **kwargs)
        except Exception as ex:
            # Catch all exceptions and report to Driver
            with driver.lock:
                # Only capture first worker exception
                if driver.worker_exception is None:
                    driver.worker_exception = ex
                driver.workers_failed += 1
            # Allow driver to check this
            driver.barrier.wait()

        driver.end_worker()
                
class FoldedActionsLockstepParallelDriver(SharingLockstepParallelDriver):
    """Lockstep system where worker processes can request actions to be added to a sequence.

    Actions will be known processes producing shared output. However,
    this parallel system can be used when the order and details of
    those possible actions is unknown a priori. Instead, workers
    perform their work, and when they run into a needed action, it
    will be "folded into" the list of actions to be performed each
    timestep.

    Actions by the workers can be arbitrarily ordered, but must be
    idential across all workers. The actions are assumed to depend on
    each other sequentailly, so that if one completes, all those after
    it are removed from the request list.

    Actions can only be requested to be added subsequent to all
    previously requested actions. This is because the driver
    preparations cannot be interrupted once it has been begun, and
    such a break in sequence would be assumed to break action
    dependency.

    When an action completes, it should return None. The action_list
    will then be shortened on the next intermission. However, the fact
    that the action has ended still needs to be acknowledge by each
    worker. This is done with a thread-local flag, including which
    timestep it was acknowledge on in case an identical action is
    added after the acknowledgement.

    Subclasses should define known actions as instance methods, with
    arguments:
      state: dict of previously prepared data in this timestep
      *args, **kwargs: other arguments
    And returns the new dict ouf prepared data.

    Typical example in the projection system: Workers go
      READ-READ-...-READ-COVAR-READ-COVAR-READ-COVAR-...

    Thread action in case where two new actions are added.
    Driver:  pn  [a1[    ]a2[  ]up]
    Worker1: .ra [  ].ra [  ]..[  ]
    Worker2: ..ra[  ]..ra[  ]..[  ]

    "Instant" actions are also supported, where a common action is
    called for by all worker threads. The worker threads are stopped
    until the driver thread finishes and can perform the action. The
    result is saved in `instant_result`.

    """
    def __init__(self, nthreads, verbosity=DEFAULT_VERBOSITY):
        super().__init__(nthreads, verbosity=verbosity)

        # Updated with lock or at intermission
        self.action_list = [] # list of (name, args, kwargs)
        self.new_action = None # new action to perform before the end of the timestep
        self.is_new_action_instant = False
        self.instant_result = None
        self.complete = False

        # Read-only, except update during intermission
        self.ending_action = None
        self.ending_clock = 0
        
        # Driver-only
        self.clock = 0
        self.drop_after_index = None

    def _intermission_threadsafe(self, next_outputs):
        # Everyone else immediately waits at barrier 2 for the data to be copied over
        while self.new_action:
            action, action_args, action_kwargs = self.new_action
            if self.is_new_action_instant:
                self.instant_result = getattr(self, 'instant_' + action)(*action_args, **action_kwargs)
                self.new_action = None
                self.lockstep_pause()
                continue
            
            # Setup the action
            getattr(self, 'setup_' + action)(*action_args, **action_kwargs)
            # Perform the new action for both curr step and next step
            curr_newouts = getattr(self, action)(self.outputs, *action_args, **action_kwargs)
            self.outputs.update(curr_newouts)
            next_newouts = getattr(self, action)(next_outputs, *action_args, **action_kwargs)
            next_outputs.update(next_newouts)
            self.action_list.append(self.new_action)
            self.new_action = None
            self.lockstep_pause()

        if self.drop_after_index is not None:
            self.ending_action = self.action_list[self.drop_after_index]
            self.ending_clock = self.clock
            self.action_list = self.action_list[:self.drop_after_index]
            self.drop_after_index = None
            
        super()._intermission_threadsafe(next_outputs)
        
    def _prepare_next(self):
        with self.lock:
            if self.complete:
                return None

        # No new actions: just run all known actions
        self.clock += 1
        outputs = {'clock': self.clock}
        self.drop_after_index = None
        for ii in range(len(self.action_list)):
            action, action_args, action_kwargs = self.action_list[ii]
            newouts = getattr(self, action)(outputs, *action_args, **action_kwargs)
            if not newouts:
                self.drop_after_index = ii
                break
            outputs.update(newouts)
            
        return outputs

    def instant_action(self, action, *args, **kwargs):
        with self.lock:
            if self.new_action:
                assert self.new_action == (action, args, kwargs), "Workers are requesting different instant actions."
            else:
                self.new_action = (action, args, kwargs)
                self.is_new_action_instant = True
                if self.verbosity > 1:
                    print("Instant " + str(self.new_action))
        self.lockstep_pause() # enter intermission and perform action
        return self.instant_result
        
    def request_action(self, local, action, *args, **kwargs):
        if 'action_index' not in local.__dict__:
            local.action_index = 0
            local.ending_acknowledge = -1
        if local.action_index < len(self.action_list) and self.action_list[local.action_index] == (action, args, kwargs):
            # already in the list and being performed
            local.action_index += 1
        elif local.action_index == len(self.action_list) and self.ending_action == (action, args, kwargs) and local.ending_acknowledge < self.ending_clock:
            local.ending_acknowledge = self.clock
        else:
            assert local.action_index == len(self.action_list), "Actions cannot be added mid-sequence."
            with self.lock:
                if self.new_action:
                    assert self.new_action == (action, args, kwargs), "Workers are requesting different driver actions."
                else:
                    self.new_action = (action, args, kwargs)
                    self.is_new_action_instant = False
                    if self.verbosity > 1:
                        print("Request " + str(self.new_action))
            self.lockstep_pause() # enter intermission and perform action
            local.action_index += 1
        return self.outputs

    def end_timestep(self, local):
        self.lockstep_pause()
        local.action_index = 0

    def end_worker(self):
        with self.lock:
            self.complete = True
        try:
            # Abort barrier, because extra barriers can be put up by driver if don't finish first
            self.lockstep_pause()
            self.barrier.abort()
        except threading.BrokenBarrierError:
            pass
