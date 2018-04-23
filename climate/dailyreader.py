import os
import numpy as np
import xarray as xr
import pandas as pd
import netcdfs
from openest.generate.fast_dataset import FastDataset
from impactcommon.math import gddkdd
from reader import YearlySplitWeatherReader, ConversionWeatherReader

class DailyWeatherReader(YearlySplitWeatherReader):
    """Exposes daily weather data, split into yearly files."""

    def __init__(self, template, year1, regionvar, *variables):
        super(DailyWeatherReader, self).__init__(template, year1, variables)
        self.time_units = 'yyyyddd'
        self.regionvar = regionvar
        self.regions = netcdfs.readncdf_single(self.find_templated(year1), regionvar, allow_missing=True)

    def get_times(self):
        times = []

        # Look for available yearly files
        for year in self.get_years():
            times.extend(year * 1000 + np.arange(1, 366))

        return times

    def get_regions(self):
        """Returns a list of all regions available."""
        return self.regions

    def get_dimension(self):
        return self.variable

    def read_iterator(self):
        # Yield data in yearly chunks
        for filename in self.file_iterator():
            yield self.prepare_ds(filename)

    def read_year(self, year):
        return self.prepare_ds(self.file_for_year(year))

    def prepare_ds(self, filename):
        try:
            ds = xr.open_dataset(filename)
            if 'time' in ds.coords:
                ds.rename({'time': 'yyyyddd', self.regionvar: 'region'}, inplace=True)
                ds['time'] = (('yyyyddd'), pd.date_range('%d-01-01' % (ds.yyyyddd[0] // 1000), periods=365))
                ds.swap_dims({'yyyyddd': 'time'}, inplace=True)
            elif 'month' in ds.coords:
                ds.rename({'month': 'time', self.regionvar: 'region'}, inplace=True)
                
            ds.load() # Collect all data now
            return ds
        except Exception as ex:
            print "Failed to prepare %s" % filename
            raise ex

    @staticmethod
    def precheck(template, year1, regionvar, *variables):
        precheck_yearly = YearlySplitWeatherReader.precheck(template, year1, variables)
        if precheck_yearly:
            return precheck_yearly

        precheck_netcdf = netcdfs.precheck_single(YearlySplitWeatherReader.find_templated_given(template, year1), regionvar)
        if precheck_netcdf:
            return precheck_netcdf

        return None

class MonthlyDimensionedWeatherReader(YearlySplitWeatherReader):
    def __init__(self, template, year1, regionvar, variable, dim):
        super(MonthlyDimensionedWeatherReader, self).__init__(template, year1, variable)
        self.time_units = 'yyyy0mm'
        self.regionvar = regionvar
        self.dim = dim
        self.regions = netcdfs.readncdf_single(self.file_for_year(year1), regionvar, allow_missing=True)
        self.dim_values = netcdfs.readncdf_single(self.file_for_year(year1), dim)

    def get_regions(self):
        """Returns a list of all regions available."""
        return self.regions

    def get_times(self):
        times = []

        # Look for available yearly files
        for year in self.get_years():
            times.extend(year * 1000 + np.arange(1, 13))

        return times

    def get_dimension(self):
        return [self.variable + '-' + str(self.dim_values[bb]) for bb in range(len(self.dim_values))]

    def read_iterator(self):
        # Yield data in yearly chunks
        for filename in self.file_iterator():
            ds = xr.open_dataset(filename)
            if 'month' in ds.coords:
                ds.rename({'month': 'time', self.regionvar: 'region'}, inplace=True)
            else:
                ds.rename({self.regionvar: 'region'}, inplace=True)
            ds = ds.transpose('time', 'region', self.dim) # Some old code may depend on T x REGIONS x K
            yield ds

    def read_year(self, year):
        ds = xr.open_dataset(self.file_for_year(year))
        if 'month' in ds.coords:
            ds.rename({'month': 'time', self.regionvar: 'region'}, inplace=True)
        else:
            ds.rename({self.regionvar: 'region'}, inplace=True)
        ds = ds.transpose('time', 'region', self.dim) # Some old code may depend on T x REGIONS x K
        return ds

class MonthlyBinnedWeatherReader(MonthlyDimensionedWeatherReader):
    """Exposes binned weather data, accumulated into months and split into yearly file."""

    def __init__(self, template, year1, regionvar, variable):
        super(MonthlyBinnedWeatherReader, self).__init__(template, year1, regionvar, variable, 'bin_limits')

    def get_dimension(self):
        return [self.variable + '-' + str(self.dim_values[bb-1]) + '-' + str(self.dim_values[bb]) for bb in range(1, len(self.dim_values))] # if dim_values = 2, single value

class YearlyBinnedWeatherReader(YearlySplitWeatherReader):
    """Exposes binned weather data, accumulated into years from a month binned file."""

    def __init__(self, template, year1, regionvar, variable):
        super(YearlyBinnedWeatherReader, self).__init__(template, year1, variable)
        self.time_units = 'yyyy000'
        self.regionvar = regionvar
        self.monthlyreader = MonthlyBinnedWeatherReader(template, year1, regionvar, variable)
        self.bin_limits = self.monthlyreader.bin_limits

    def get_times(self):
        return self.get_years()

    def get_dimension(self):
        return self.monthlyreader.get_dimension()

    def read_iterator(self):
        # Yield data summed across years
        for ds in self.monthlyreader.read_iterator():
            ds = ds.groupby('time.year').sum()
            ds.rename({self.regionvar: 'region'}, inplace=True)
            yield ds.rename({'year': 'time'})

    def read_year(self, year):
        ds = self.monthlyreader.read_year(year)
        ds = ds.groupby('time.year').sum()
        ds.rename({self.regionvar: 'region'}, inplace=True)
        return ds.rename({'year': 'time'})

class GDDKDDReader(ConversionWeatherReader):
    def __init__(self, reader, tminvar, tmaxvar, lower, upper):
        self.tminvar = tminvar
        self.tmaxvar = tmaxvar
        super(GDDKDDReader, self).__init__(reader, lambda x: x, lambda ds: self.convert(ds, lower, upper))
         
    def convert(ds, lower, upper):
        allgdd = np.zeros((len(ds.time), len(ds.region)))
        allkdd = np.zeros((len(ds.time), len(ds.region)))
        for ii in range(len(ds.region)):
            allgdd[:, ii], allkdd[:, ii] = gddkdd.get_gddkdd(ds[self.tminvar][:, ii],
                                                             ds[self.tmaxvar][:, ii], lower, upper)

        gddname = 'gdd-%d-%d' % (lower, upper)
        kddname = 'kdd-%d' % upper
        return fast_dataset.FastDataset({gddname: (('time', 'region'), allgdd),
                                         kddname: (('time', 'region'), allkdd)},
                                        {'time': ds.time, 'region': ds.region}, attrs=ds.attrs)
