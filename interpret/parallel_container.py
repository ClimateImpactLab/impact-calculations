import threading
from . import container
from generate import parallel_weather, pvalses, multithread
from adaptation import parallel_econmodel

preload = container.preload
get_bundle_iterator = container.get_bundle_iterator

## NOTE: All logic in effectset can be at the slave level with shared data

class WeatherCovariatorLockstepParallelMaster(multithread.FoldedActionsLockstepParallelMaster):
    def __init__(self, bundle, covariator, mcdraws):
        super(WeatherCovariatorLockstepParallelMaster, self).__init__(mcdraws)
        self.bundle = bundle
        self.covariator = covariator

        # Active iterators
        self.weatheriter = None
        
    def setup_yearbundles(self, *request_args, **request_kwargs):
        assert self.weatheriter is None
        self.weatheriter = self.bundle.yearbundles(*request_args, **request_kwargs)

    def yearbundles(self, outputs, *request_args, **request_kwargs):
        try:
            year, ds = next(self.weatheriter)
            return {'year': year, 'ds': ds}
        except StopIteration:
            self.weatheriter = None
            return None # stop this and following actions

def produce(targetdir, weatherbundle, economicmodel, pvals, config, push_callback=None, suffix='', profile=False, diagnosefile=False):
    assert config['cores'] > 1, "More than one core needed."
    assert pvals is None, "Slaves must create their own pvals."
    assert push_callback is None and suffix == '' and not profile and not diagnosefile, "Cannot use diagnostic options."

    print("Setting up parallel processing...")
    master = WeatherCovariatorLockstepParallelMaster(weatherbundle, None, config['cores'] - 1)
    master.loop(slave_produce, targetdir, config)

def slave_produce(proc, master, masterdir, config):
    # Create the thread local data
    local = threading.local()

    # Create the object for claiming directories
    claim_timeout = config.get('timeout', 12) * 60*60
    statman = paralog.StatusManager('generate', "slave generate " + str(proc), 'logs', claim_timeout)

    for batch in configs.get_batch_iter(config):
        # Construct a pvals and targetdir
        if 'mcmaster' in masterdir:
            targetdir = masterdir.replace('mcmaster', 'batch' + str(proc + 1))
            pvals = pvalses.get_montecarlo_pvals(config)
        elif 'pemaster' in masterdir:
            targetdir = masterdir.replace('pemaster', 'batch' + str(proc + 1))
            pvals = pvalses.ConstantPvals(.5)
        else:
            raise ValueError("Master directory not named as expected: " + masterdir)
        
        # Claim the directory
        with master.lock:
            if not configs.claim_targetdir(statman, targetdir, False, config):
                continue

        # Wrap weatherbundle
        weatherbundle = parallel_weather.SlaveParallelWeatherBundle(master, local)
        economicmodel = parallel_econmodel.SlaveParallelSSPEconomicModel()
    
        container.produce(targetdir, weatherbundle, economicmodel, pvals, config)
