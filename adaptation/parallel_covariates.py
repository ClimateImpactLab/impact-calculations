from generate import parallel_weather
from . import covariates, parallel_econmodel

def is_parallel(weatherbundle, economicmodel, config):
    return isinstance(weatherbundle, parallel_weather.SlaveParallelWeatherBundle) and isinstance(economicmodel, parallel_econmodel.SlaveParallelSSPEconomicModel)

def create_covariator(specconf, weatherbundle, economicmodel):
    assert isinstance(weatherbundle, parallel_weather.SlaveParallelWeatherBundle)
    covariator = weatherbundle.master.instant_action("create_covariator", specconf)
    return SlaveParallelCovariator(covariator)

class SlaveParallelCovariator(covariates.Covariator):
    def __init__(self, master, source):
        super(SlaveParallelCovariator, self).__init__(self, source.maxbaseline, config=source.config)
        self.master = master
        self.source = source

    def get_yearcovar(self, region):
        return self.source.get_yearcovar(region)

    def get_current(self, region):
        return self.source.get_current(region)
        
    def offer_update(self, region, year, ds):
        self.master.request_action('covariate_update', self.source)
        assert self.source.lastyear.get(region, -np.inf) == year, "ReadonlyCovariator can only be called after master updates."
        return self.source.get_current(region)
