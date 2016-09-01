from netCDF4 import Dataset
from reader import WeatherReader
from scipy.stats import norm
import netcdfs, forecasts
import numpy as np

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
            yield month + aheads[0], valuesgen.next()

        lastvalues = forecasts.readncdf_lastpred(self.filepath, self.variable)
        for ii in range(1, len(aheads)):
            yield months[-1] + aheads[ii], lastvalues[ii, :]

class MonthlyStochasticForecastReader(MonthlyForecastReader):
    """
    Expose monthly forecast results, as probabilistic values.
    """

    def __init__(self, filepath, variable, lead=0, qval=.5):
        super(MonthlyStochasticForecastReader, self).__init__(filepath, 'mean', lead)

        self.variable = variable
        self.qval = qval

    def read_iterator(self):
        months = self.get_times()
        meansgen = forecasts.readncdf_allpred(self.filepath, "mean", self.lead)
        allsdevs = list(forecasts.readncdf_allpred(self.filepath, "stddev", self.lead))
        for month in months:
            yield month, norm.ppf(self.qval, meansgen.next(), allsdevs[month % 12])

class MonthlyZScoreForecastReader(MonthlyStochasticForecastReader):
    """
    Translates into z-scores on-the-fly, using climate data.
    """

    def __init__(self, filepath, climatepath, variable, lead=0, qval=.5):
        super(MonthlyZScoreForecastReader, self).__init__(filepath, variable, lead, qval)
        version_climate, units_climate = netcdfs.readmeta(climatepath, 'mean')
        assert self.units == units_climate

        self.climatepath = climatepath

    def get_dimension(self):
        return ['Z(' + self.variable + ')']

    def read_iterator(self):
        means = list(forecasts.readncdf_allpred(self.climatepath, "mean", self.lead))
        sdevs = list(forecasts.readncdf_allpred(self.climatepath, "stddev", self.lead))

        for month, weather in super(MonthlyZScoreForecastReader, self).read_iterator():
            yield month, (weather - means[month % 12]) / sdevs[month % 12]
