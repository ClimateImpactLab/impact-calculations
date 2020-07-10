from generate import parallel_weather
from . import covariates, parallel_econmodel

def is_parallel(weatherbundle, economicmodel=None, config=None):
    if economicmodel is not None:
        return isinstance(weatherbundle, parallel_weather.SlaveParallelWeatherBundle) and isinstance(economicmodel, parallel_econmodel.SlaveParallelSSPEconomicModel)
    else:
        return isinstance(weatherbundle, parallel_weather.SlaveParallelWeatherBundle)
    
def create_covariator(specconf, weatherbundle, economicmodel):
    assert isinstance(weatherbundle, parallel_weather.SlaveParallelWeatherBundle)
    covariator = weatherbundle.master.instant_action("create_covariator", specconf)
    return SlaveParallelCovariator(weatherbundle.master, covariator, weatherbundle.local)

class SlaveParallelCovariator(covariates.Covariator):
    def __init__(self, master, source, local):
        super(SlaveParallelCovariator, self).__init__(source.startupdateyear, config={'yearcovarscale': source.yearcovarscale})
        self.master = master
        self.source = source
        self.local = local
        self.last_offer_year = None

    def get_yearcovar(self, region):
        return self.source.get_yearcovar(region)

    def get_current(self, region):
        return self.source.get_current(region)
        
    def offer_update(self, region, year, ds):
        if self.last_offer_year != year: # only do once per year
            self.master.request_action(self.local, 'covariate_update', self.source)
            self.last_offer_year = year
        assert self.source.lastyear.get(region, -np.inf) == year, "ReadonlyCovariator can only be called after master updates."
        return self.source.get_current(region)
