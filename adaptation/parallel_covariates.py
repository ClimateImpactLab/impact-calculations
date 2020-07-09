def is_parallel(weatherbundle, economicmodel, config):
    return isinstance(weatherbundle, SlaveParallelWeatherBundle) and isinstance(economicmodel, SlaveParallelSSPEconomicModel)

def create_covariator(specconf, weatherbundle, economicmodel):
    covariator = master.instant_action("create_covariator", specconf)
    return SlaveParallelCovariator(covariator)

class SlaveParallelCovariator(Covariator):
    def __init__(self, master):
        super(ReadonlyCovariator, self).__init__(self, master.maxbaseline, config=master.config)
        self.master = master

    def get_yearcovar(self, region):
        return master.get_yearcovar(region)

    def get_current(self, region):
        return master.get_current(region)
        
    def offer_update(self, region, year, ds):
        master.request_action('covariate_update', self.master)
        assert master.lastyear.get(region, -np.inf) == year, "ReadonlyCovariator can only be called after master updates."
        return master.get_current(region)
