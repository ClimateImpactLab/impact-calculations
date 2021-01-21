import time
import numpy as np
from generate import multithread

worker_sleep = .01
processed = {}

class MyTestLockstepParallelDriver(multithread.LockstepParallelDriver):
    def __init__(self, mcdraws, preptime):
        super(MyTestLockstepParallelDriver, self).__init__(mcdraws)
        self.preptime = preptime
        self.timestep = 0
        
    def _prepare_next(self):
        truetime = np.random.normal(self.preptime, self.preptime) ** 2
        time.sleep(truetime)
        self.timestep += 1
        if self.timestep == 10:
            print("Driver: END")
            return None

        print("Driver: " + str(self.timestep))
        return self.timestep

# Uses worker_sleep, fills in processed = {proc: [...]}
def worker_process(proc, driver):
    print("Worker: START")
    
    while True:
        outputs = driver.outputs
        if outputs is None:
            break

        truetime = np.random.normal(worker_sleep, worker_sleep) ** 2
        time.sleep(truetime)
        print("Worker: " + str(outputs))
        processed[proc].append(outputs)
        driver.lockstep_pause()

    print("Worker: END")

def test_lockstep():
    global worker_sleep, processed
    
    ## Test with worker < driver
    worker_sleep = .05
    processed = {}
    for proc in range(5):
        processed[proc] = []

    driver = MyTestLockstepParallelDriver(5, .1)
    driver.loop(worker_process)

    for proc in range(5):
        np.testing.assert_equal(processed[proc], np.arange(1, 10))

    # Test with worker > driver
    worker_sleep = .2
    processed = {}
    for proc in range(5):
        processed[proc] = []

    driver = MyTestLockstepParallelDriver(5, .1)
    driver.loop(worker_process)

    for proc in range(5):
        np.testing.assert_equal(processed[proc], np.arange(1, 10))

if __name__ == '__main__':
    test_lockstep()
