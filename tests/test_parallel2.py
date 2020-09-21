import time, threading
import numpy as np
from generate import multithread

## Determine what the result should look like
weather = np.random.normal(size=100)
weathersum = np.cumsum(weather)
covars = [weathersum[19]] * 20 + list(weathersum[20:])
assert len(covars) == len(weather)
results_true = weather * covars

class MyTestFoldedActionsLockstepParallelMaster(multithread.FoldedActionsLockstepParallelMaster):
    def __init__(self, mcdraws):
        super(MyTestFoldedActionsLockstepParallelMaster, self).__init__(mcdraws)
        self.covarval = 0
        self.weatheriter = None

    def setup_iterate_weather(self, count):
        assert self.weatheriter is None
        self.weatheriter = enumerate(weather[:count])

    def iterate_weather(self, outputs, count):
        try:
            ii, val = next(self.weatheriter)
            return {'weather': val}
        except StopIteration:
            self.weatheriter = None
            return None # stop this and following actions

    def setup_calc_covar(self, baseline):
        self.covarval = baseline
    
    def calc_covar(self, outputs, baseline):
        self.covarval += outputs['weather']
        return {'covar': self.covarval}

def weatherbundle(master, local, count=len(weather)):
    while True:
        outputs = master.request_action(local, 'iterate_weather', count)
        if 'weather' not in outputs:
            break
        yield outputs['weather']

def updatecovar(master, local, baseline, weather):
    outputs = master.request_action(local, 'calc_covar', baseline)
    return outputs['covar']
        
def slave_process(proc, master):
    # Create the thread local data
    local = threading.local()
    
    # Calculate baseline covar
    baseline = 0
    for weather in weatherbundle(master, local, 20):
        baseline += weather
        master.end_timestep(local)

    print("MIDP" + str(proc))
        
    # Calculate results
    year = 0
    results = []
    for weather in weatherbundle(master, local):
        year += 1
        if year > 20:
            covar = updatecovar(master, local, baseline, weather)
            results.append(weather * covar)
        else:
            results.append(weather * baseline)
        master.end_timestep(local)

    np.testing.assert_equal(results, results_true)
    master.end_slave()
    print("DONE" + str(proc))

def test_folded():
    master = MyTestFoldedActionsLockstepParallelMaster(5)
    master.loop(slave_process)

if __name__ == '__main__':
    test_folded()
