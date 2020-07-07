from . import container
from generate import parallel_weather, pvalses
from adaptation import parallel_econmodel

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
    
    master = WeatherCovariatorLockstepParallelMaster(weatherbundle, None, config['cores'] - 1)
    master.loop(slave_produce, targetdir, config)

def slave_produce(proc, master, masterdir, config):
    # Create the thread local data
    local = threading.local()

    # Construct a pvals and targetdir
    if 'parallelmc' in masterdir:
        targetdir = masterdir.replace('parallelmc', 'batch' + str(proc + 1))
        pvals = pvalses.get_montecarlo_pvals(config)
    elif 'parallelpe' in masterdir:
        targetdir = masterdir.replace('parallelpe', 'batch' + str(proc + 1))
        pvals = pvalses.ConstantPvals(.5)
    else:
        raise ValueError("Master directory not named as expected.")

    # Wrap weatherbundle
    weatherbundle = parallel_weather.SlaveParallelWeatherBundle(master, local)
    economicmodel = parallel_economdel.SlaveParallelSSPEconomicModel()
    
    container.produce(targetdir, weatherbundle, economicmodel, pvals, config)
