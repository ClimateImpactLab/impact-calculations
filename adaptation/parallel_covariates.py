import numpy as np
from generate import parallel_weather
from . import covariates, parallel_econmodel

def is_parallel(weatherbundle, economicmodel=None, config=None):
    if economicmodel is not None:
        return isinstance(weatherbundle, parallel_weather.SlaveParallelWeatherBundle) and isinstance(economicmodel, parallel_econmodel.SlaveParallelSSPEconomicModel)
    else:
        return isinstance(weatherbundle, parallel_weather.SlaveParallelWeatherBundle)
    
def create_covariator(specconf, weatherbundle, economicmodel, farmer):
    assert isinstance(weatherbundle, parallel_weather.SlaveParallelWeatherBundle)
    covariator = weatherbundle.master.instant_action("create_covariator", specconf)
    return SlaveParallelCovariator(weatherbundle.master, covariator, weatherbundle.local, farmer)

class SlaveParallelCovariator(covariates.Covariator):
    def __init__(self, master, source, local, farmer):
        super(SlaveParallelCovariator, self).__init__(source.startupdateyear, config={'yearcovarscale': source.yearcovarscale})
        self.master = master
        self.source = source
        self.local = local
        self.farmer = farmer
        self.last_offer_year = None
        self.curr_covars = {}
        self.curr_years = {}
        for region in master.regions:
            self.curr_covars[region] = self.source.get_current(region)
            self.curr_years[region] = self.source.get_yearcovar(region)

    def get_yearcovar(self, region):
        return self.curr_years[region]

    def get_current(self, region):
        return self.curr_covars[region]
        
    def offer_update(self, region, year, ds):
        if self.last_offer_year != year: # only do once per year
            outputs = self.master.request_action(self.local, 'covariate_update', self.source, self.farmer)
            self.curr_covars = outputs['curr_covars']
            self.curr_years = outputs['curr_years']
            self.last_offer_year = year
        return self.get_current(region)
