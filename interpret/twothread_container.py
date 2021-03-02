"""Simplified multithreading with a driver and worker thread.

A driver thread prepares shared data for each
timestep, consisting of weather data and (after 2015) covariate
data. The worker threads performs its work with wrapped objects providing
read-only access to this shared data.

The driver thread does not decide on the order of operations. Instead,
it waits for worker threads to request various actions. The worker
thread proceeds in lockstep, so that as soon as it requests an action
the first time, it stops. At that point, the driver is given time to
perform the action first immediately, and then it will continue to
perform it in future timesteps, while the workers are working on the
last timestep's values.

This allows all processing logic in effectset to be performed at the
worker level. That is, the code below this point is unchanged and run
by workers, and the code does not need special conditions for parallel
processing.

"""

from . import container, parallel_container

preload = container.preload
get_bundle_iterator = container.get_bundle_iterator

def produce(targetdir, weatherbundle, economicmodel, pvals, config, **kwargs):
    """Split the processing to the workers."""
    assert config['threads'] == 2, "Exactly two threads needed."

    print("Setting up parallel processing...")
    my_regions = configs.get_regions(weatherbundle.regions, config.get('filter-region', None))
    driver = parallel_container.WeatherCovariatorLockstepParallelDriver(weatherbundle, economicmodel, config, config['threads'] - 1, seed, my_regions)
    driver.loop(worker_produce, targetdir, config, pvals, **kwargs)

def worker_produce(proc, driver, targetdir, config, pvals, **kwargs):
    # Create the thread local data
    local = threading.local()

    driver.any_worker_working = True  # report that we are working

    # Wrap weatherbundle
    weatherbundle = parallel_weather.WorkerParallelWeatherBundle(driver, local)
    economicmodel = parallel_econmodel.WorkerParallelSSPEconomicModel(driver, local)

    container.produce(targetdir, weatherbundle, economicmodel, pvals, config, **kwargs)
