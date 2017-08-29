import numpy as np

class SpaceTimeData(object):
    def __init__(self, year0, year1, regions):
        self.year0 = year0
        self.year1 = year1
        self.regions = regions

class SpaceTimeLoadedData(SpaceTimeData):
    def __init__(self, year0, year1, regions, array, ifmissing=None):
        super(SpaceTimeLoadedData, self).__init__(year0, year1, regions)
        self.array = array # as YEAR x REGION
        self.indices = {regions[ii]: ii for ii in range(len(regions))}
        if ifmissing == 'mean':
            self.missing = np.mean(self.array, 1)
        elif ifmissing == 'logmean':
            self.missing = np.exp(np.mean(np.log(self.array), 1))
        else:
            self.missing = None
            
    def get_time(self, region):
        #ii = self.regions.index(region)
        ii = self.indices.get(region, None)
        if ii is None:
            return self.missing
        
        return self.array[:, ii]

class SpaceTimeLazyData(SpaceTimeData):
    def __init__(self, year0, year1, regions, get_time):
        super(SpaceTimeLazyData, self).__init__(year0, year1, regions)
        self.get_time = get_time

    def get_time(self, region):
        return self.get_time(region)

class SpaceTimeProductData(SpaceTimeData):
    def __init__(self, year0, year1, regions, spdata, factor):
        super(SpaceTimeProductData, self).__init__(year0, year1, regions)
        self.spdata = spdata
        self.factor = factor

    def get_time(self, region):
        return self.spdata.get_time(region) * self.factor

class SpaceTimeBipartiteData(SpaceTimeData):
    """Loads the historical data in __init__, and the future data in load()."""
    
    def load(self, year0, year1, model, scenario):
        """Return a SpaceTimeData for the given model and scenario."""
        raise NotImplementedError

class SpaceTimeProductBipartiteData(SpaceTimeBipartiteData):
    def __init__(self, year0, year1, regions, spdata, factor):
        super(SpaceTimeProductBipartiteData, self).__init__(year0, year1, regions)
        self.spdata = spdata
        self.factor = factor

    def load(self, year0, year1, model, scenario):
        return SpaceTimeProductData(year0, year1, self.regions, self.spdata.load(year0, year1, model, scenario), self.factor)
    
class SpaceTimeUnipartiteData(SpaceTimeBipartiteData):
    def __init__(self, year0, year1, regions, loader):
        super(SpaceTimeUnipartiteData, self).__init__(year0, year1, regions)
        self.loader = loader
    
    def load(self, year0, year1, model, scenario):
        return self.loader(year0, year1, self.regions, model, scenario)
