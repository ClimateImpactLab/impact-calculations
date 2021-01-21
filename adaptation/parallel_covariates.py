"""
Covariator object used by workers during parallel processing runs.
"""

import numpy as np
from generate import parallel_weather
from . import covariates
    
def create_covariator(specconf, weatherbundle, economicmodel, farmer):
    """Ask the driver create the covariator."""
    assert isinstance(weatherbundle, parallel_weather.WorkerParallelWeatherBundle)
    covariator = weatherbundle.driver.instant_action("create_covariator", specconf)
    return WorkerParallelCovariator(weatherbundle.driver, covariator, weatherbundle.local, farmer)

class WorkerParallelCovariator(covariates.Covariator):
    """Thread-safe covariator, which requests updates through the driver."""
    def __init__(self, driver, source, local, farmer):
        super(WorkerParallelCovariator, self).__init__(source.startupdateyear, config={'yearcovarscale': source.yearcovarscale})
        self.driver = driver
        self.source = source
        self.local = local
        self.farmer = farmer
        self.last_offer_year = None
        self.curr_covars = {}
        self.curr_years = {}
        for region in driver.regions:
            self.curr_covars[region] = self.source.get_current(region)
            self.curr_years[region] = self.source.get_yearcovar(region)

    def get_yearcovar(self, region):
        return self.curr_years[region]

    def get_current(self, region):
        return self.curr_covars[region]
        
    def offer_update(self, region, year, ds):
        if self.last_offer_year != year: # only do once per year
            outputs = self.driver.request_action(self.local, 'covariate_update', self.source, self.farmer)
            self.curr_covars = outputs['curr_covars']
            self.curr_years = outputs['curr_years']
            self.last_offer_year = year
        return self.get_current(region)
