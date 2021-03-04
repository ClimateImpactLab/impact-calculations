"""Configuration-based calculation processing under multithreading.

Under multithreading, a driver thread prepares shared data for each
timestep, consisting of weather data and (after 2015) covariate
data. Worker threads perform their work with wrapped objects providing
read-only access to this shared data.

The driver thread does not decide on the order of operations. Instead,
it waits for worker threads to request various actions. All worker
threads proceed in lockstep, so that if one is going to request an
action, all will. At that point, the driver is given time to perform
the action first immediately, and then it will continue to perform it
in future timesteps, while the workers are working on the last
timestep's values.

This allows all processing logic in effectset to be performed at the
worker level. That is, the code below this point is unchanged and run
by workers, and the code does not need special conditions for parallel
processing.
"""

import os, threading
from openest.generate import fast_dataset
from . import container, configs, specification
from generate import parallel_weather, pvalses, multithread, weather
from adaptation import parallel_econmodel, curvegen
from impactlab_tools.utils import paralog

preload = container.preload
get_bundle_iterator = container.get_bundle_iterator

class WeatherCovariatorLockstepParallelDriver(multithread.FoldedActionsLockstepParallelDriver):
    """The driver thread controller.

    Contains shared sources of data (weatherbundle, economicmodel),
    maintains shared data production (through weatheriter and
    farm_curvegen), and defines actions available to the workers. These
    actions are called when a wrapped worker object (like
    WorkerParallelWeatherBundle) needs shared data.
    """
    def __init__(self, weatherbundle, economicmodel, config, mcdraws, seed, regions=None):
        super(WeatherCovariatorLockstepParallelDriver, self).__init__(mcdraws)
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

        # Has any worker found work to do?
        self.any_worker_working = False
        
    def setup_yearbundles(self, *request_args, **request_kwargs):
        """Start producing yearly weather data. Called by a `request_action`."""
        assert self.weatheriter is None
        self.weatheriter = self.weatherbundle.yearbundles(*request_args, **request_kwargs)

    def yearbundles(self, outputs, *request_args, **request_kwargs):
        """Collects the next year of weather data. Called by system after a `request_action`."""
        try:
            year, ds = next(self.weatheriter)
            return {'year': year, 'ds': ds}
        except StopIteration:
            self.weatheriter = None
            return None # stop this and following actions

    def instant_create_covariator(self, specconf):
        """Create a covariator using the shared weatherbundle and economic model.

        Called by an `instant_action` call. Returns driver thread's
        covariator; needs to be wrapped in a WorkerParallelCovariator.
        """
        return specification.create_covariator(specconf, self.weatherbundle, self.economicmodel, config=self.config)

    def instant_make_historical(self):
        """Cause the shared weatherbundle to be replaced by a historical version."""
        print("Historical")
        self.weatherbundle = weather.HistoricalWeatherBundle.make_historical(self.weatherbundle, self.seed)
    
    def setup_covariate_update(self, covariator, farmer):
        """Start updating covariates. Called by a `request_action`."""
        self.covariator = covariator
        self.farm_curvegen = curvegen.FarmerCurveGenerator(curvegen.ConstantCurveGenerator(['unused'], 'unused', curvegen.FlatCurve(0)),
                                                           covariator, farmer, save_curve=False)
        # Call with every region, so that last_curves is filled out
        for region in self.regions:
            self.farm_curvegen.get_curve(region, 2010, weather=None)

    def covariate_update(self, outputs, covariator, farmer):
        """Update covariates on each timestep. Called by system after a `request_action`."""
        curr_covars = {}
        curr_years = {}
        for region, subds in fast_dataset.region_groupby(outputs['ds'], outputs['year'], self.regions, self.region_indices):
            self.farm_curvegen.get_curve(region, subds.year, weather=subds)
            curr_years[region] = self.covariator.get_yearcovar(region)
            curr_covars[region] = self.covariator.get_current(region)

        return dict(covars_update_year=outputs['year'], curr_covars=curr_covars, curr_years=curr_years)

def produce(targetdir, weatherbundle, economicmodel, pvals, config, push_callback=None, suffix='', profile=False, diagnosefile=False):
    """Split the processing to the workers."""
    assert config['threads'] > 1, "More than one thread needed."
    assert isinstance(pvals, pvalses.PlaceholderPvals), "Workers must create their own pvals."
    if push_callback is not None or suffix != '' or profile or diagnosefile:
        print("WARNING: Cannot use diagnostic options.")

    if config['mode'] == 'testparallelpe':
        seed = None
    else:
        # Always create a new seed
        driver_pvals = pvals.get_montecarlo_pvals()
        seed = driver_pvals['histclim'].get_seed('yearorder')
    
    print("Setting up parallel processing...")
    my_regions = configs.get_regions(weatherbundle.regions, config.get('filter-region', None))
    driver = WeatherCovariatorLockstepParallelDriver(weatherbundle, economicmodel, config, config['threads'] - 1, seed, my_regions)
    driver.loop(worker_produce, targetdir, config, pvals)

def worker_produce(proc, driver, driverdir, config, placeholder_pvals):
    """
    Find a single batch and produce data into it.
    """
    # Create the thread local data
    local = threading.local()

    # Create the object for claiming directories
    claim_timeout = config.get('timeout', 12) * 60*60
    produced_one = False
    
    for batch in configs.get_batch_iter(config):
        # Construct a pvals and targetdir
        if 'mcdriver' in driverdir:
            targetdir = driverdir.replace('mcdriver', 'batch' + str(batch))
            pvals = placeholder_pvals.get_montecarlo_pvals()
            pvals['histclim'].set_seed('yearorder', driver.seed)
        elif 'pedriver' in driverdir:
            targetdir = driverdir.replace('pedriver', 'batch' + str(batch))
            pvals = pvalses.ConstantPvals(.5)
        else:
            raise ValueError("Driver directory not named as expected: " + driverdir)
        
        # Claim the directory
        with driver.lock:
            if not configs.claim_targetdir(configs.global_statman, targetdir, False, config):
                continue
            driver.any_worker_working = True  # report that we are working
        produced_one = True

        # Wrap weatherbundle
        weatherbundle = parallel_weather.WorkerParallelWeatherBundle(driver, local)
        economicmodel = parallel_econmodel.WorkerParallelSSPEconomicModel(driver, local)

        container.produce(targetdir, weatherbundle, economicmodel, pvals, config)

        # Make historical
        driver.instant_action('make_historical')
        pvals.lock()

        container.produce(targetdir, weatherbundle, economicmodel, pvals, config, suffix='-histclim')
        
        pvalses.make_pval_file(targetdir, pvals)
        configs.global_statman.release(targetdir, "Generated")
        os.system("chmod g+rw " + os.path.join(targetdir, "*"))
        driver.end_worker()
        break

    # We could not find a batch
    if not produced_one:
        driver.lockstep_pause()
        # Has any worker succeeded in finding work?
        with driver.lock:
            any_worker_working = driver.any_worker_working
        if any_worker_working:
            # We need to keep pausing until other workers are done
            while True:
                try:
                    self.lockstep_pause()
                except threading.BrokenBarrierError:
                    break
    else:
        # Nothing to wait for, nothing to do
        driver.end_worker()
