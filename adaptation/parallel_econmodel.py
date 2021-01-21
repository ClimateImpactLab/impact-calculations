"""
SSPEconomicModel object used by workers during parallel processing runs.
"""

def is_parallel(economicmodel):
    return isinstance(economicmodel, WorkerParallelSSPEconomicModel)

class WorkerParallelSSPEconomicModel(object):
    """Thread-safe SSPEconomicModel-mimic. As normally used, always raises errors."""
    def __init__(self, driver, local, saved_baselines=None):
        self.driver = driver
        self.local = local
        if saved_baselines is None:
            saved_baselines = {}
        self.saved_baselines = saved_baselines

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

    def __getattr__(self, name):
        return getattr(self.driver.economicmodel, name)
