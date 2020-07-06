import time
import numpy as np
from generate import multithread

class TestLockstepParallelMaster(multithread.LockstepParallelMaster):
    def __init__(self, mcdraws, preptime):
        super(TestLockstepParallelMaster, self).__init__(mcdraws)
        self.preptime = preptime
        self.timestep = 0
        
    def _prepare_next(self):
        truetime = np.random.normal(self.preptime, self.preptime) ** 2
        time.sleep(truetime)
        self.timestep += 1
        if self.timestep == 10:
            print("Master: END")
            return None

        print("Master: " + str(self.timestep))
        return self.timestep

# Uses slave_sleep, fills in processed = {proc: [...]}
def slave_process(proc, master):
    print("Slave: START")
    
    while True:
        outputs = master.outputs
        if outputs is None:
            break

        truetime = np.random.normal(slave_sleep, slave_sleep) ** 2
        time.sleep(truetime)
        print("Slave: " + str(outputs))
        processed[proc].append(outputs)
        master.lockstep_pause()

    print("Slave: END")

## Test with slave < master
slave_sleep = .05
processed = {}
for proc in range(5):
    processed[proc] = []

master = TestLockstepParallelMaster(5, .1)
master.loop(slave_process)

for proc in range(5):
    np.testing.assert_equal(processed[proc], np.arange(1, 10))

# Test with slave > master
slave_sleep = .2
processed = {}
for proc in range(5):
    processed[proc] = []

master = TestLockstepParallelMaster(5, .1)
master.loop(slave_process)

for proc in range(5):
    np.testing.assert_equal(processed[proc], np.arange(1, 10))
