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
        """Return a timeseries vector for the given region
        """
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
    """SpaceTimeData subclass given `get_time` when initialized

    Parameters
    ----------
    year0 : int
        The first year of the data
    year1 : int
        The last year of the data (inclusive of year1)
    regions : sequence of str
        Region names are generally drawn from the hierarchy.
    get_time : Callable
        Callable taking a single input argument, usually a str region name.
    """
    def __init__(self, year0, year1, regions, get_time):
        super(SpaceTimeLazyData, self).__init__(year0, year1, regions)
        self.get_time = get_time

    def get_time(self, region):
        """Get timeseries for a region
        
        Pass `region` to `self.get_time` and return output"""
        return self.get_time(region)

class SpaceTimeProductData(SpaceTimeData):
    """Create a SpaceTime as the product of two SpaceTimeData-likes

    Parameters
    ----------
    year0 : int
        The first year of the data
    year1 : int
        The last year of the data (inclusive of year1)
    regions : sequence of str
        Region names are generally drawn from the hierarchy.
    spdata1 : SpaceTimeData-like
    spdata2 : SpaceTimeData-like
    combiner : Callable, optional
        Callable taking two args, the output of `*.get_time()` called from
        `spdata1` and `spdata2`. By default, returns the product of the two
        timeseries.
    """
    def __init__(self, year0, year1, regions, spdata1, spdata2, combiner=lambda x, y: x * y):
        super(SpaceTimeProductData, self).__init__(year0, year1, regions)
        self.spdata1 = spdata1
        self.spdata2 = spdata2
        self.combiner = combiner

    def get_time(self, region):
        """Return timeseries for a region
        """
        datum1 = self.spdata1.get_time(region)
        datum2 = self.spdata2.get_time(region)
        if datum1 is None:
            return None
        if datum2 is None:
            return None

        # Drop extra years from either datum
        datum1 = np.array(datum1)
        datum2 = np.array(datum2)
        if datum1.shape != datum2.shape and len(datum1.shape) == len(datum2.shape) and len(datum1.shape) > 0:
            # This is the case where we're trying to combine equivalent arrays, except one is longer
            min_shape = tuple([slice(0, min(datum1.shape[ii], datum2.shape[ii]), None) for ii in range(len(datum1.shape))])
            datum1 = datum1[min_shape]
            datum2 = datum2[min_shape]

        return self.combiner(datum1, datum2)

class SpaceTimeBipartiteData(SpaceTimeData):
    """ Abstract class for loading historical and future data in two steps

    Loads the historical data in __init__, and the future data in load().
    """
    def load(self, year0, year1, model, scenario):
        """Return a SpaceTimeData for the given model and scenario."""
        raise NotImplementedError

class SpaceTimeBipartiteFromProviderData(SpaceTimeData):
    """SpaceTimeBipartite from Providers

    Parameters
    ----------
    Provider : impactcommon.exogenous_economy.provider.BySpaceProvider-like or impactcommon.exogenous_economy.provider.BySpaceTimeProvider-like
    year0 : int
        The first year of the data
    year1 : int
        The last year of the data (inclusive of year1)
    regions : sequence of str
        Region names are generally drawn from the hierarchy.
    """
    def __init__(self, Provider, year0, year1, regions):
        super(SpaceTimeBipartiteFromProviderData, self).__init__(year0, year1, regions)
        self.Provider = Provider

    def load(self, year0, year1, model, scenario):
        """Load data from `self.Provider`

        Parameters
        ----------
        year0 : int
            The first year of the data.
        year1 : int
            The last year of the data (inclusive of year1).
        model : str
            Model (IAM) to draw from.
        scenario : str
            Scenario (SSP) to use.

        Returns
        -------
        SpaceTimeLazyData
        """
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
            prepared = prepared[:year1 - year0 + 1]
        elif year1 - year0 + 1 > len(prepared):
            prepared.extend([prepared[-1]] * (year1 - year0 + 1 - len(prepared)))

        return prepared
            
class SpaceTimeProductBipartiteData(SpaceTimeBipartiteData):
    """Create a SpaceTimeBipartite as the product of two SpaceTimeBipartiteData-likes

    Parameters
    ----------
    year0 : int
        The first year of the data
    year1 : int
        The last year of the data (inclusive of year1)
    regions : sequence of str
        Region names are generally drawn from the hierarchy.
    spdata1 : SpaceTimeBipartiteData-like
    spdata2 : SpaceTimeBipartiteData-like
    combiner : Callable, optional
        Callable taking two args, the output of `*.get_time()` called from
        `spdata1` and `spdata2`. By default, returns the product of the two
        timeseries.
    """
    def __init__(self, year0, year1, regions, spdata1, spdata2, combiner=lambda x, y: x * y):
        super(SpaceTimeProductBipartiteData, self).__init__(year0, year1, regions)
        self.spdata1 = spdata1
        self.spdata2 = spdata2
        self.combiner = combiner

    def load(self, year0, year1, model, scenario):
        """Load data from `self.Provider`

        Parameters
        ----------
        year0 : int
            The first year of the data.
        year1 : int
            The last year of the data (inclusive of year1).
        model : str
            Model (IAM) to draw from.
        scenario : str
            Scenario (SSP) to use.

        Returns
        -------
        SpaceTimeProductData
        """
        return SpaceTimeProductData(year0, year1, self.regions, self.spdata1.load(year0, year1, model, scenario), self.spdata2.load(year0, year1, model, scenario), self.combiner)

class SpaceTimeUnipartiteData(SpaceTimeBipartiteData):
    def __init__(self, year0, year1, regions, loader):
        super(SpaceTimeUnipartiteData, self).__init__(year0, year1, regions)
        self.loader = loader
    
    def load(self, year0, year1, model, scenario):
        return self.loader(year0, year1, self.regions, model, scenario)

class SpaceTimeConstantData(SpaceTimeBipartiteData):
    """SpaceTimeBipartiteData using constant data
    """
    def __init__(self, constant):
        super(SpaceTimeConstantData, self).__init__(-np.inf, np.inf, None)
        self.constant = constant

    def get_time(self, region):
        """Returns `self.constant`, regardless of input
        """
        return self.constant

    def load(self, year0, year1, model, scenario):
        """Returns `self`, regardless of input
        """
        return self
    
class SpaceTimeSpatialOnlyData(SpaceTimeBipartiteData):
    """SpaceTimeBipartiteData with only spatial (region) mapping available

    Parameters
    ----------
    mapping : dict
        {region-key: value} mapping.
    """
    def __init__(self, mapping):
        super(SpaceTimeSpatialOnlyData, self).__init__(-np.inf, np.inf, list(mapping.keys()))
        self.mapping = mapping

    def get_time(self, region):
        """Return a timeseries vector for the given region
        """
        return self.mapping[region]

    def load(self, year0, year1, model, scenario):
        """Returns `self` regardless of input
        """
        return self

class SpaceTimeMatrixData(SpaceTimeData):
    """SpaceTimeData-like for 2D np.matrix data

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
        super(SpaceTimeMatrixData, self).__init__(year0, year1, regions)
        self.array = array # as YEAR x REGION
        self.ifmissing = ifmissing
        self.adm3fallback = adm3fallback

    def load(self, year0, year1, model, scenario):
        """
        Parameters
        ----------
        year0 : int
            The first year of the data.
        year1 : int
            The last year of the data (inclusive of year1).
        model : str
            Model (IAM) to draw from.
        scenario : str
            Scenario (SSP) to use.

        Returns
        -------
        SpaceTimeLoadedData
        """
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
    
