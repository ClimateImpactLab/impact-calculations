import numpy as np

class SpaceTimeData(object):
    def __init__(self, year0, year1, regions):
        self.year0 = year0
        self.year1 = year1
        self.regions = regions

class SpaceTimeLoadedData(SpaceTimeData):
    def __init__(self, year0, year1, regions, array, ifmissing=None, adm3fallback=False):
        super(SpaceTimeLoadedData, self).__init__(year0, year1, regions)
        self.array = array # as YEAR x REGION
        self.indices = {regions[ii]: ii for ii in range(len(regions))}
        
        if ifmissing == 'mean':
            self.missing = np.mean(self.array, 1)
        elif ifmissing == 'logmean':
            self.missing = np.exp(np.mean(np.log(self.array), 1))
        else:
            self.missing = None

        self.adm3fallback = adm3fallback
            
    def get_time(self, region):
        ii = self.indices.get(region, None)
        if ii is None:
            if self.adm3fallback and len(regions) > 3:
                return self.get_time(regions[:3])
            
            return self.missing
        
        return self.array[:, ii]

class SpaceTimeLazyData(SpaceTimeData):
    def __init__(self, year0, year1, regions, get_time):
        super(SpaceTimeLazyData, self).__init__(year0, year1, regions)
        self.get_time = get_time

    def get_time(self, region):
        return self.get_time(region)

class SpaceTimeProductData(SpaceTimeData):
    def __init__(self, year0, year1, regions, spdata1, spdata2, combiner=lambda x, y: x * y):
        super(SpaceTimeProductData, self).__init__(year0, year1, regions)
        self.spdata1 = spdata1
        self.spdata2 = spdata2
        self.combiner = combiner

    def get_time(self, region):
        return self.combiner(self.spdata1.get_time(region), self.spdata2.get_time(region))

class SpaceTimeBipartiteData(SpaceTimeData):
    """Loads the historical data in __init__, and the future data in load()."""
    
    def load(self, year0, year1, model, scenario):
        """Return a SpaceTimeData for the given model and scenario."""
        raise NotImplementedError

class SpaceTimeProductBipartiteData(SpaceTimeBipartiteData):
    def __init__(self, year0, year1, regions, spdata1, spdata2, combiner=lambda x, y: x * y):
        super(SpaceTimeProductBipartiteData, self).__init__(year0, year1, regions)
        self.spdata1 = spdata1
        self.spdata2 = spdata2
        self.combiner = combiner

    def load(self, year0, year1, model, scenario):
        return SpaceTimeProductData(year0, year1, self.regions, self.spdata1.load(year0, year1, model, scenario), self.spdata2.load(year0, year1, model, scenario), self.combiner)

class SpaceTimeUnipartiteData(SpaceTimeBipartiteData):
    def __init__(self, year0, year1, regions, loader):
        super(SpaceTimeUnipartiteData, self).__init__(year0, year1, regions)
        self.loader = loader
    
    def load(self, year0, year1, model, scenario):
        return self.loader(year0, year1, self.regions, model, scenario)

class SpaceTimeConstantData(SpaceTimeBipartiteData):
    def __init__(self, constant):
        super(SpaceTimeConstantData, self).__init__(-np.inf, np.inf, None)
        self.constant = constant

    def get_time(self, region):
        return self.constant

    def load(self, year0, year1, model, scenario):
        return self
    
class SpaceTimeSpatialOnlyData(SpaceTimeBipartiteData):
    def __init__(self, mapping):
        super(SpaceTimeSpatialOnlyData, self).__init__(-np.inf, np.inf, mapping.keys())
        self.mapping = mapping

    def get_time(self, region):
        return self.mapping[region]

    def load(self, year0, year1, model, scenario):
        return self
        
class SpaceTimeTransformedData(SpaceTimeBipartiteData):
    def __init__(self, mapping, transform):
        super(SpaceTimeTransformedData, self).__init__(-np.inf, np.inf, mapping.keys())
        self.mapping = mapping
        self.transform = transform

    def get_time(self, region):
        return self.transform(self.mapping[region])

    def load(self, year0, year1, model, scenario):
        return self
        
