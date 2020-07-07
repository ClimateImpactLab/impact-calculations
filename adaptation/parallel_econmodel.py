class SlaveParallelSSPEconomicModel(object):
    def __init__(self):
        # Currently just a dummy for raising exceptions
        # self.economicmodel = economicmodel
        pass

    def reset(self):
        pass

    def baseline_prepared(self, maxbaseline, numeconyears, func):
        # This should be a request
        raise NotImplementedError

    def get_loggdppc_year(self, region, year):
        # This should be a request
        raise NotImplementedError

    def get_popop_year(self, region, year):
        # This should be a request
        raise NotImplementedError
