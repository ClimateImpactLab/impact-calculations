class SlaveParallelSSPEconomicModel(object):
    def __init__(self, saved_baselines):
        # Currently just a dummy for raising exceptions
        self.saved_baselines = saved_baselines
        pass

    def reset(self):
        pass

    def baseline_prepared(self, maxbaseline, numeconyears, func, stdfunckey=None):
        assert stdfunckey is not None, "Only standard economic baselines are supported."
        key = (maxbaseline, numeconyears, stdfunckey)
        if key in self.saved_baselines:
            return self.saved_baselines[key]

        raise ValueError("Unknown economic baseline: " + str(key))

    def get_loggdppc_year(self, region, year):
        # This should be a request
        raise NotImplementedError

    def get_popop_year(self, region, year):
        # This should be a request
        raise NotImplementedError
