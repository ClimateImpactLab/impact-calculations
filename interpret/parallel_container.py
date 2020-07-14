import os, threading
from openest.generate import fast_dataset
from . import container, configs, specification
from generate import parallel_weather, pvalses, multithread, weather
from adaptation import parallel_econmodel, curvegen
from impactlab_tools.utils import paralog

preload = container.preload
get_bundle_iterator = container.get_bundle_iterator

## NOTE: All logic in effectset can be at the slave level with shared data

class WeatherCovariatorLockstepParallelMaster(multithread.FoldedActionsLockstepParallelMaster):
    def __init__(self, weatherbundle, economicmodel, config, mcdraws, seed, regions=None):
        super(WeatherCovariatorLockstepParallelMaster, self).__init__(mcdraws)
        self.weatherbundle = weatherbundle
        self.economicmodel = economicmodel
        self.config = config
        self.seed = seed

        if regions is None:
            self.regions = weatherbundle.regions
        else:
            self.regions = regions
        self.region_indices = {region: weatherbundle.regions.index(region) for region in self.regions}
        
        # Active iteration objects
        self.weatheriter = None
        self.farm_curvegen = None
        self.covariator = None
        
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

    def instant_make_historical(self):
        print("Historical")
        self.weatherbundle = weather.HistoricalWeatherBundle.make_historical(self.weatherbundle, self.seed)
    
    def setup_covariate_update(self, covariator, farmer):
        self.covariator = covariator
        self.farm_curvegen = curvegen.FarmerCurveGenerator(curvegen.ConstantCurveGenerator(['unused'], 'unused', curvegen.FlatCurve(0)),
                                                           covariator, farmer, save_curve=False)
        # Call with every region, so that last_curves is filled out
        for region in self.weatherbundle.regions:
            self.farm_curvegen.get_curve(region, 2010, weather=None)

    def covariate_update(self, outputs, covariator, farmer):
        curr_covars = {}
        curr_years = {}
        for region, subds in fast_dataset.region_groupby(outputs['ds'], outputs['year'], self.regions, self.region_indices):
            self.farm_curvegen.get_curve(region, subds.year, weather=subds)
            curr_years[region] = self.covariator.get_yearcovar(region)
            curr_covars[region] = self.covariator.get_current(region)

        return dict(covars_update_year=outputs['year'], curr_covars=curr_covars, curr_years=curr_years)

def produce(targetdir, weatherbundle, economicmodel, pvals, config, push_callback=None, suffix='', profile=False, diagnosefile=False):
    assert config['cores'] > 1, "More than one core needed."
    assert pvals is None, "Slaves must create their own pvals."
    assert push_callback is None and suffix == '' and not profile and not diagnosefile, "Cannot use diagnostic options."

    if config['mode'] == 'testparallelpe':
        seed = None
    else:
        # Always create a new seed
        pvals = pvalses.OnDemandRandomPvals()
        seed = pvals['histclim'].get_seed('yearorder')
    
    print("Setting up parallel processing...")
    my_regions = configs.get_regions(weatherbundle.regions, config.get('filter-region', None))
    master = WeatherCovariatorLockstepParallelMaster(weatherbundle, economicmodel, config, config['cores'] - 1, seed, my_regions)
    master.loop(slave_produce, targetdir, config)

def slave_produce(proc, master, masterdir, config):
    # Create the thread local data
    local = threading.local()

    # Create the object for claiming directories
    claim_timeout = config.get('timeout', 12) * 60*60

    for batch in configs.get_batch_iter(config):
        # Construct a pvals and targetdir
        if 'mcmaster' in masterdir:
            targetdir = masterdir.replace('mcmaster', 'batch' + str(batch))
            pvals = pvalses.get_montecarlo_pvals(config)
            pvals['histclim'].set_seed('yearorder', master.seed)
        elif 'pemaster' in masterdir:
            targetdir = masterdir.replace('pemaster', 'batch' + str(batch))
            pvals = pvalses.ConstantPvals(.5)
        else:
            raise ValueError("Master directory not named as expected: " + masterdir)
        
        # Claim the directory
        with master.lock:
            if not configs.claim_targetdir(configs.global_statman, targetdir, False, config):
                continue

        # Wrap weatherbundle
        weatherbundle = parallel_weather.SlaveParallelWeatherBundle(master, local)
        economicmodel = parallel_econmodel.SlaveParallelSSPEconomicModel(master, local)

        container.produce(targetdir, weatherbundle, economicmodel, pvals, config)

        # Make historical
        master.instant_action('make_historical')
        pvals.lock()

        container.produce(targetdir, weatherbundle, economicmodel, pvals, config, suffix='-histclim')
        
        pvalses.make_pval_file(targetdir, pvals)
        configs.global_statman.release(targetdir, "Generated")
        os.system("chmod g+rw " + os.path.join(targetdir, "*"))
        master.end_slave()
        break
