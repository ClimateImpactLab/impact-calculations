from netCDF4 import Dataset
from reader import WeatherReader
from scipy.stats import norm
import netcdfs, forecasts
import numpy as np
from openest.generate.weatherslice import ForecastMonthlyWeatherSlice
from datastore import irregions

class MonthlyForecastReader(WeatherReader):
    """
    Expose monthly forecast values, ignoring any uncertainty information.
    """
    def __init__(self, filepath, variable):
        version, units = netcdfs.readmeta(filepath, variable)
        version, time_units = netcdfs.readmeta(filepath, 'S')
        super(MonthlyForecastReader, self).__init__(version, units, time_units)

        self.filepath = filepath
        self.variable = variable
        self.regions = irregions.load_regions("hierarchy.csv", [])

    def get_start_ahead_times(self):
        """Return list of months"""
        rootgrp = Dataset(self.filepath, 'r', format='NETCDF4')
        months = rootgrp.variables['S'][:]
        aheads = rootgrp.variables['L'][:]
        rootgrp.close()

        return months, aheads

    def get_times(self):
        months, aheads = self.get_start_ahead_times()
        return list(months + aheads[0]) + list(months[-1] + aheads[1:])

    def get_dimension(self):
        return [self.variable]

    def read_iterator(self):
        months, aheads = self.get_start_ahead_times()
        valuesgen = forecasts.readncdf_allpred(self.filepath, self.variable, 0)
        for month in months:
            yield ForecastMonthlyWeatherSlice(month, aheads[0], valuesgen.next())

        lastvalues = forecasts.readncdf_lastpred(self.filepath, self.variable)
        for ii in range(1, len(aheads)):
            yield ForecastMonthlyWeatherSlice(months[-1], aheads[ii], lastvalues[ii, :])

class MonthlyStochasticForecastReader(MonthlyForecastReader):
    """
    Expose monthly forecast results, as probabilistic values.
    """
    def __init__(self, filepath, variable, qval=.5):
        super(MonthlyStochasticForecastReader, self).__init__(filepath, 'mean')

        self.dim_variable = variable
        self.qval = qval

    def get_dimension(self):
        return [self.dim_variable]

    def read_iterator(self):
        allsdevs = forecasts.readncdf_allmonths(self.filepath, 'stddev')[:, 0, :] # only use 1st look-ahead, since we'll adjust month later

        for weatherslice in super(MonthlyStochasticForecastReader, self).read_iterator():
            weatherslice.weathers = norm.ppf(self.qval, weatherslice.weathers, allsdevs[int(weatherslice.times[0]) % 12, :])
            yield weatherslice

class MonthlyZScoreForecastOTFReader(MonthlyStochasticForecastReader):
    """
    Translates into z-scores on-the-fly, using climate data.
    """
    def __init__(self, filepath, climatepath, variable, qval=.5):
        super(MonthlyZScoreForecastOTFReader, self).__init__(filepath, variable, qval)
        version_climate, units_climate = netcdfs.readmeta(climatepath, 'mean')
        assert self.units == units_climate

        self.climatepath = climatepath

    def get_dimension(self):
        return ['Z(' + self.variable + ')']

    def read_iterator(self):
        means = forecasts.readncdf_allmonths(self.climatepath, 'mean')
        sdevs = forecasts.readncdf_allmonths(self.climatepath, 'stddev')

        for weatherslice in super(MonthlyZScoreForecastOTFReader, self).read_iterator():
            assert weatherslice.weathers.shape[0] == 1

            weathers = (weatherslice.weathers[0, :] - means[weatherslice.month % 12, int(weatherslice.ahead - 1.5), :]) / sdevs[weatherslice.month % 12, int(weatherslice.ahead - 1.5), :]
            weatherslice.weathers = np.expand_dims(weathers, axis=0)
            yield weatherslice

class MonthlyZScoreForecastReader(MonthlyForecastReader):
    """
    Reads from z-score files
    """
    def __init__(self, zscorepath, normstddevpath, variable, qval=.5):
        super(MonthlyZScoreForecastReader, self).__init__(zscorepath, 'z-scores')
        version_stddev, units_stddev = netcdfs.readmeta(normstddevpath, 'stddev')
        #assert self.units == units_stddev, "%s <> %s" % (self.units, units_stddev)

        self.normstddevpath = normstddevpath
        self.dim_variable = variable # overwrite, now that intialization is done using 'z-scores'
        self.qval = qval

    def get_dimension(self):
        return [self.dim_variable]

    def read_iterator(self):
        allsdevs = forecasts.readncdf_allmonths(self.normstddevpath, "stddev")[:, 0, :]

        for weatherslice in super(MonthlyZScoreForecastReader, self).read_iterator():
            # undo adding ahead, since we take out the 1.5 lead for allsdevs
            weatherslice.weathers = norm.ppf(self.qval, weather, allsdevs[int(weatherslice.times[0] - 1.5) % 12, :])
            yield weatherslice

class TransformedReader(WeatherReader):
    def __init__(self, source):
        self.source = source
        super(TransformedReader, self).__init__(source.version, source.units, source.time_units)

    def read_iterator(self):
        raise NotImplementedError()

    def get_times(self):
        return self.source.get_times()

    def get_dimension(self):
        return self.source.get_dimension()
            
class CountryDuplicatedReader(TransformedReader):
    def __init__(self, source, regions):
        super(CountryDuplicatedReader, self).__init__(source)
        self.regions = regions
        
        countryindex = {} # {iso: index}
        for ii in range(len(self.source.regions)):
            countryindex[self.source.regions[ii]] = ii
        self.countryindex = countryindex
            
    def read_iterator(self):
        for weatherslice in self.source.read_iterator():
            weathers = np.zeros((weatherslice.weathers.shape[0], len(self.regions)))
            for ii in range(len(self.regions)):
                weathers[:, ii] = weatherslice.weathers[:, self.countryindex[self.regions[ii][:3]]]

            weatherslice.weathers = weathers
            yield weatherslice

class CountryAveragedReader(TransformedReader):
    def __init__(self, source):
        super(CountryAveragedReader, self).__init__(source)

        self.regions = np.unique(map(lambda region: region[:3], source.regions))

    def read_iterator(self):
        for weatherslice in self.source.read_iterator():
            bycountry = {} # {iso: [values]}
            regions = self.source.regions # All IR
            for ii in range(len(regions)):
                if regions[ii][:3] in bycountry:
                    bycountry[regions[ii][:3]].append(weatherslice.weathers[:, ii])
                else:
                    bycountry[regions[ii][:3]] = [weatherslice.weathers[:, ii]]

            weathers = np.zeros((weatherslice.weathers.shape[0], len(self.regions)))
            for ii in range(len(self.regions)): # Just countries
                weathers[:, ii] = np.mean(bycountry[self.regions[ii]])
                
            yield ForecastMonthlyWeatherSlice(weatherslice.month, weatherslice.ahead, weathers, ignore_regionnum=True)

class CountryDeviationsReader(TransformedReader):
    def __init__(self, source):
        super(CountryDeviationsReader, self).__init__(source)

    def read_iterator(self):
        for weatherslice in self.source.read_iterator():
            weathers = weatherslice.weathers
            bycountry = {} # {iso: [values]}
            regions = self.source.regions
            for ii in range(len(regions)):
                if regions[ii][:3] in bycountry:
                    bycountry[regions[ii][:3]].append(weathers[:, ii])
                else:
                    bycountry[regions[ii][:3]] = [weathers[:, ii]]

            for country in bycountry:
                bycountry[country] = np.mean(bycountry[country])

            for ii in range(len(regions)):
                weatherslice.weathers[:, ii] = weatherslice.weathers[:, ii] - bycountry[regions[ii][:3]]

            yield weatherslice
