import threading
from . import container, configs, specification
from generate import parallel_weather, pvalses, multithread
from adaptation import parallel_econmodel
from impactlab_tools.utils import paralog

preload = container.preload
get_bundle_iterator = container.get_bundle_iterator

## NOTE: All logic in effectset can be at the slave level with shared data

class WeatherCovariatorLockstepParallelMaster(multithread.FoldedActionsLockstepParallelMaster):
    def __init__(self, weatherbundle, economicmodel, config, mcdraws, regions=None):
        super(WeatherCovariatorLockstepParallelMaster, self).__init__(mcdraws)
        self.weatherbundle = weatherbundle
        self.economicmodel = economicmodel
        self.config = config

        if regions is None:
            self.regions = weatherbundle.regions
        else:
            self.regions = regions
        self.region_indices = {region: weatherbundle.regions.index(region) for region in self.regions}
        
        # Active iteration objects
        self.weatheriter = None
        self.farm_curvegen = None
        
    def setup_yearbundles(self, *request_args, **request_kwargs):
        assert self.weatheriter is None
        self.weatheriter = self.weatherbundle.yearbundles(*request_args, **request_kwargs)

    def yearbundles(self, outputs, *request_args, **request_kwargs):
        try:
            year, ds = next(self.weatheriter)
            return {'year': year, 'ds': ds}
        except StopIteration:
            self.weatheriter = None
            return None # stop this and following actions

    def instant_create_covariator(self, specconf): # Returns master thread's covariator; needs to be wrapped
        return specification.create_covariator(specconf, self.weatherbundle, self.economicmodel, config=self.config)

    def setup_covariate_update(self, covariator, farmer):
        self.farm_curvegen = curvegen.FarmerCurveGenerator(curvegen.FlatCurve(0), covariator, farmer, save_curve=False)

    def covariate_update(self, outputs, covariator, farmer):
        for region, subds in fast_dataset.region_groupby(outputs['ds'], outputs['year'], self.regions, self.region_indices):
            self.farm_curvegen.get_curve(region, subds.year, weather=subds)
            
def produce(targetdir, weatherbundle, economicmodel, pvals, config, push_callback=None, suffix='', profile=False, diagnosefile=False):
    assert config['cores'] > 1, "More than one core needed."
    assert pvals is None, "Slaves must create their own pvals."
    assert push_callback is None and suffix == '' and not profile and not diagnosefile, "Cannot use diagnostic options."

    print("Setting up parallel processing...")
    my_regions = configs.get_regions(weatherbundle.regions, config.get('filter-region', None))
    master = WeatherCovariatorLockstepParallelMaster(weatherbundle, economicmodel, config, config['cores'] - 1, my_regions)
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
        economicmodel = parallel_econmodel.SlaveParallelSSPEconomicModel(master, local)

        print("START %d/%d" % (batch, proc))
        container.produce(targetdir, weatherbundle, economicmodel, pvals, config)
