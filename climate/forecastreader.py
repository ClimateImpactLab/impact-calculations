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
        allsdevs = forecasts.readncdf_allmonths(self.filepath, 'stddev')
        allsdevs = np.vstack((allsdevs[:, 0, :], allsdevs[-1, 1:, :]))

        tt = 0
        for weatherslice in super(MonthlyStochasticForecastReader, self).read_iterator():
            weatherslice.weathers = norm.ppf(self.qval, weatherslice.weathers, allsdevs[tt, :])
            tt += 1
            yield weatherslice

class TransformedReader(WeatherReader):
    def __init__(self, source):
        self.source = source
        super(TransformedReader, self).__init__(source.version, source.units, source.time_units)
        if hasattr(source, 'regions'):
            self.regions = source.regions

    def read_iterator(self):
        raise NotImplementedError()

    def get_times(self):
        return self.source.get_times()

    def get_dimension(self):
        return self.source.get_dimension()

class MonthlyZScoreForecastReader(TransformedReader):
    """
    Translates into z-scores on-the-fly, using climate data.
    """
    def __init__(self, source, meanclimate, sdevclimate, climvar):
        super(MonthlyZScoreForecastReader, self).__init__(source)
        version_climate, units_climate = netcdfs.readmeta(sdevclimate, climvar)
        assert self.units == units_climate

        self.meanclimate = meanclimate
        self.sdevclimate = sdevclimate
        self.climvar = climvar

    def get_dimension(self):
        return ['Z(' + self.source.dimension()[0] + ')']

    def read_iterator(self):
        means = forecasts.readncdf_allmonths(self.meanclimate, self.climvar)
        sdevs = forecasts.readncdf_allmonths(self.sdevclimate, self.climvar)
        
        if means.shape[1] > sdevs.shape[1]:
            # Sdevs is country-level; need to average means and reorder sdevs
            bycountry = forecasts.get_means(irregions.load_regions("hierarchy.csv", []), lambda ii: means[:, ii])

            sdevs_regions = list(netcdfs.readncdf_single(self.sdevclimate, 'ISO'))
            ordered_sdevs = np.zeros(sdevs.shape)
            country_means = np.zeros(sdevs.shape)
            regions = self.source.regions # Just countries
            for ii in range(len(regions)):
                country_means[:, ii] = bycountry[regions[ii]]
                ordered_sdevs[:, ii] = sdevs[:, sdevs_regions.index(regions[ii])]
            means = country_means
            sdevs = ordered_sdevs

        for weatherslice in self.source.read_iterator():
            assert weatherslice.weathers.shape[0] == 1

            weathers = (weatherslice.weathers[0, :] - means[int(weatherslice.month + weatherslice.ahead) % 12, :]) / sdevs[int(weatherslice.month + weatherslice.ahead) % 12, :]
            weatherslice.weathers = np.expand_dims(weathers, axis=0)
            yield weatherslice
            
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
            bycountry = forecasts.get_means(self.source.regions, lambda ii: weatherslice.weathers[:, ii])

            weathers = np.zeros((weatherslice.weathers.shape[0], len(self.regions)))
            for ii in range(len(self.regions)): # Just countries
                weathers[:, ii] = bycountry[self.regions[ii]]
                
            yield ForecastMonthlyWeatherSlice(weatherslice.month, weatherslice.ahead, weathers, ignore_regionnum=True)

class CountryDeviationsReader(TransformedReader):
    def __init__(self, source):
        super(CountryDeviationsReader, self).__init__(source)

    def read_iterator(self):
        for weatherslice in self.source.read_iterator():
            weathers = weatherslice.weathers
            bycountry = forecasts.get_means(self.source.regions, lambda ii: weathers[:, ii])

            regions = self.source.regions
            for ii in range(len(regions)):
                weatherslice.weathers[:, ii] = weatherslice.weathers[:, ii] - bycountry[regions[ii][:3]]

            yield weatherslice
