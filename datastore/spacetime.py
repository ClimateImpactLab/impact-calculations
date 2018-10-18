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

class SpaceTimeBipartiteFromProviderData(SpaceTimeData):
    def __init__(self, Provider, year0, year1, regions):
        super(SpaceTimeBipartiteFromProviderData, self).__init__(year0, year1, regions)

    def load(self, year0, year1, model, scenario):
        provider = Provider(model, scenario)
        return SpaceTimeLazyData(year0, year1, self.regions, lambda region: self.adjustlen(year0, year1, provider.get_startyear(),
                                                                                           provider.get_timeseries(region)))

    def adjustlen(year0, year1, startyear, series):
        if startyear < year0:
            prepared = series[year0 - startyear:]
        elif startyear > year0:
            prepared = [series[0]] * (startyear - year0)
            prepared.extend(series)
        else:
            prepared = series

        if year1 - year0 < len(prepared):
            prepared = prepared[:year1 - year0]
        elif year1 - year0 > len(prepared):
            prepared.extend([prepared[-1]] * (year1 - year0 - len(prepared)))

        return prepared
            
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
    
