import copy, threading

## NEW SETUP:

class LockstepParallelMaster(object):
    """Facilitates a parallel programming structure with master and slave threads.

    The processing occurs on a timestep clock. For each timestep,
    the master thread prepares the data for the next timestep, while
    the slaves process that data. Barriers are used to synchronize all
    threads at the end of each timestep.
    """
    def __init__(self, mcdraws):
        self.mcdraws = mcdraws
        self.barrier = threading.Barrier(mcdraws + 1, timeout=threading.TIMEOUT_MAX)

        # Read-only, except update during intermission
        self.outputs = None

    def loop(self, start, *args):
        self.outputs = self._prepare_next()
        # Start all threads
        for proc in range(self.mcdraws):
            thread = threading.Thread(None, start, args=tuple([proc, self] + list(args)))
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
        
    
class FoldedActionsLockstepParallelMaster(LockstepParallelMaster):
    """Lockstep system where slave processes can request actions to be added to a sequence.

    Actions will be known processes producing shared output. However,
    this parallel system can be used when the order and details of
    those possible actions is unknown a priori. Instead, slaves
    perform their work, and when they run into a needed action, it
    will be "folded into" the list of actions to be performed each
    timestep.

    Actions by the slaves can be arbitrarily ordered, but must be
    idential across all slaves. The actions are assumed to depend on
    each other sequentailly, so that if one completes, all those after
    it are removed from the request list.

    Actions can only be requested to be added subsequent to all
    previously requested actions. This is because the master
    preparations cannot be interrupted once it has been begun, and
    such a break in sequence would be assumed to break action
    dependency.

    When an action completes, it should return None. The action_list
    will then be shortened on the next intermission. However, the fact
    that the action has ended still needs to be acknowledge by each
    slave. This is done with a thread-local flag, including which
    timestep it was acknowledge on in case an identical action is
    added after the acknowledgement.

    Subclasses should define known actions as instance methods, with
    arguments:
      state: dict of previously prepared data in this timestep
      *args, **kwargs: other arguments
    And returns the new dict ouf prepared data.

    Typical example in the projection system: Slaves go
      READ-READ-...-READ-COVAR-READ-COVAR-READ-COVAR-...

    Thread action in case where two new actions are added.
    Master: pn  [a1[    ]a2[  ]up]
    Slave1: .ra [  ].ra [  ]..[  ]
    Slave2: ..ra[  ]..ra[  ]..[  ]

    """
    def __init__(self, mcdraws):
        super(FoldedActionsLockstepParallelMaster, self).__init__(mcdraws)
        self.lock = threading.Lock() # for accessing action_list

        # Updated with lock or at intermission
        self.action_list = [] # list of (name, args, kwargs)
        self.new_action = None # new action to perform before the end of the timestep
        self.complete = False

        # Read-only, except update during intermission
        self.ending_action = None
        
        # Master-only
        self.clock = 0
        self.drop_after_index = None

    def _intermission_threadsafe(self, next_outputs):
        # Everyone else immediately waits at barrier 2 for the data to be copied over
        while self.new_action:
            action, action_args, action_kwargs = self.new_action
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
            self.action_list = self.action_list[:self.drop_after_index]
            self.drop_after_index = None
            
        super(FoldedActionsLockstepParallelMaster, self)._intermission_threadsafe(next_outputs)
        
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

    def request_action(self, local, action, *args, **kwargs):
        if 'action_index' not in local.__dict__:
            local.action_index = 0
            local.ending_acknowledge = -1
        if local.action_index < len(self.action_list) and self.action_list[local.action_index] == (action, args, kwargs):
            # already in the list and being performed
            local.action_index += 1
        elif local.action_index == len(self.action_list) and self.ending_action == (action, args, kwargs) and local.ending_acknowledge < self.clock:
            local.ending_acknowledge = self.clock
        else:
            assert local.action_index == len(self.action_list), "Actions cannot be added mid-sequence."
            with self.lock:
                if self.new_action:
                    assert self.new_action == (action, args, kwargs), "Slaves are requesting different actions."
                else:
                    self.new_action = (action, args, kwargs)
            self.lockstep_pause() # enter intermission and perform action
            local.action_index += 1
        return self.outputs

    def end_timestep(self, local):
        self.lockstep_pause()
        local.action_index = 0

    def end_slave(self):
        with self.lock:
            self.complete = True
        try:
            # Abort barrier, because extra barriers can be put up by master if don't finish first
            self.lockstep_pause()
            self.barrier.abort()
        except threading.BrokenBarrierError:
            pass
