"""
Classes for handling lazy-loaded spatiotemporal data.
"""

import numpy as np
import numpy.matlib

class SpaceTimeData(object):
    """SpaceTimeData is the top-level class for providing spatiotemporal data.
    It provides no data, but has information on the range of years and regions covered.

    Parameters
    ----------
    year0 : int
        The first year of the data
    year1 : int
        The last year of the data (inclusive of year1)
    regions : sequence of str
        Region names are generally drawn from the hierarchy.

    """
    def __init__(self, year0, year1, regions):
        self.year0 = year0
        self.year1 = year1
        self.regions = regions

    def load(self, year0, year1, model, scenario):
        """Load data for the given model and scenario. Return an object that
        supports the `get_time` method."""
        raise NotImplementedError()
        
class SpaceTimeLoadedData(SpaceTimeData):
    """SpaceTimeLoadedData contains the entire collection of space-time data as a matrix.
    
    Parameters
    ----------
    year0 : int
        The first year of the data
    year1 : int
        The last year of the data (inclusive of year1)
    regions : sequence of str
        Region names are generally drawn from the hierarchy.
    array : array_like
        Should have (year1 - year0 + 1) rows and len(regions) columns.
    ifmissing : None or 'mean' or 'logmean'
        When a region is not in the data, return None or the mean or logmean timeseries.
    adm3fallback : bool
        If True, when a region is not in the data, instead the 3-character ADM0 suffix will be queried.

    """
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
        """Return a timeseries vector for the given region."""
        ii = self.indices.get(region, None)
        if ii is None:
            if self.adm3fallback and len(region) > 3:
                return self.get_time(region[:3])
            
            return self.missing
        
        return self.array[:, ii]

    def load(self, year0, year1, model, scenario):
        """Load the requied data. It's already loaded, so just return this."""
        return self

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
        datum1 = self.spdata1.get_time(region)
        datum2 = self.spdata2.get_time(region)
        if datum1 is None:
            return None
        if datum2 is None:
            return None
        return self.combiner(datum1, datum2)

class SpaceTimeBipartiteData(SpaceTimeData):
    """Loads the historical data in __init__, and the future data in load()."""
    
    def load(self, year0, year1, model, scenario):
        """Return a SpaceTimeData for the given model and scenario."""
        raise NotImplementedError

class SpaceTimeBipartiteFromProviderData(SpaceTimeData):
    def __init__(self, Provider, year0, year1, regions):
        super(SpaceTimeBipartiteFromProviderData, self).__init__(year0, year1, regions)
        self.Provider = Provider

    def load(self, year0, year1, model, scenario):
        provider = self.Provider(model, scenario)
        return SpaceTimeLazyData(year0, year1, self.regions, lambda region: self.adjustlen(year0, year1, provider.get_startyear(),
                                                                                           provider.get_timeseries(region)))

    def adjustlen(self, year0, year1, startyear, series):
        if startyear < year0:
            prepared = series[year0 - startyear:]
        elif startyear > year0:
            prepared = [series[0]] * (startyear - year0)
            prepared.extend(series)
        else:
            prepared = series

        # Inclusive of the last year
        if year1 - year0 + 1 < len(prepared):
            prepared = prepared[:year1 - year0]
        elif year1 - year0 + 1 > len(prepared):
            prepared.extend([prepared[-1]] * (year1 - year0 + 1 - len(prepared)))

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
    
class SpaceTimeSpatialOnlyData(SpaceTimeBipartiteData):
    def __init__(self, mapping):
        super(SpaceTimeSpatialOnlyData, self).__init__(-np.inf, np.inf, mapping.keys())
        self.mapping = mapping

    def get_time(self, region):
        return self.mapping[region]

    def load(self, year0, year1, model, scenario):
        return self

class SpaceTimeMatrixData(SpaceTimeData):
    def __init__(self, year0, year1, regions, array, ifmissing=None, adm3fallback=False):
        super(SpaceTimeMatrixData, self).__init__(year0, year1, regions)
        self.array = array # as YEAR x REGION
        self.ifmissing = ifmissing
        self.adm3fallback = adm3fallback

    def load(self, year0, year1, model, scenario):
        if year0 == self.year0 and year1 == self.year1:
            array = self.array
        else:
            array = np.zeros(((year1 - year0 + 1), self.array.shape[1]))
            if self.year0 > year0:
                array[:(self.year0 - year0), :] = np.matlib.repmat(self.array[0, :], self.year0 - year0, 1)
                selfii0 = 0
                arrayii0 = self.year0 - year0
            else:
                selfii0 = year0 - self.year0
                arrayii0 = 0
                
            if self.year1 < year1:
                array[(year1 - self.year1):, :] = np.matlib.repmat(self.array[-1, :], year1 - self.year1, 1)
                selfii1 = self.array.shape[0]
                arrayii1 = array.shape[0] - (year1 - self.year1)
            else:
                selfii1 = self.array.shape[0] - (self.year1 - year1)
                arrayii1 = array.shape[0]
                
            array[arrayii0:arrayii1] = self.array[selfii0:selfii1]
                
        return SpaceTimeLoadedData(year0, year1, self.regions, array, self.ifmissing, self.adm3fallback)
    
