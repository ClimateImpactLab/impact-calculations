from netCDF4 import Dataset
from reader import WeatherReader
from scipy.stats import norm
import netcdfs, forecasts
import numpy as np
import xarray as xr

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

        ds = xr.open_dataset(self.filepath, decode_times=False)
        for month in months:
            yield ds[self.variable].sel(S=month, L=1.5)
        
        for ii in range(1, len(aheads)):
            yield ds[self.variable].sel(S=months[-1], L=aheads[ii])

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

        for ds in super(MonthlyStochasticForecastReader, self).read_iterator():
            ds['mean'] = norm.ppf(self.qval, ds.mean, allsdevs[int(ds.S[0]) % 12, :])
            yield ds

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

        for ds in super(MonthlyZScoreForecastOTFReader, self).read_iterator():
            ds['mean'] = (ds.mean[0, :] - means[ds.S % 12, int(ds.L - 1.5), :]) / sdevs[ds.S % 12, int(ds.L - 1.5), :]
            yield ds

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

        for ds in super(MonthlyZScoreForecastReader, self).read_iterator():
            # undo adding ahead, since we take out the 1.5 lead for allsdevs
            ds['mean'] = norm.ppf(self.qval, weather, allsdevs[int(ds.S[0] + ds.L[0] - 1.5) % 12, :])
            yield ds
