import os
import numpy as np
import xarray as xr
import pandas as pd
import netcdfs
from reader import YearlySplitWeatherReader

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
        ds = xr.open_dataset(filename)
        ds.rename({'time': 'yyyyddd', self.regionvar: 'region'}, inplace=True)
        ds['time'] = (('yyyyddd'), pd.date_range('%d-01-01' % (ds.yyyyddd[0] // 1000), periods=365))
        ds.swap_dims({'yyyyddd': 'time'}, inplace=True)
        ds.load() # Collect all data now
        return ds
    
class MonthlyBinnedWeatherReader(YearlySplitWeatherReader):
    """Exposes binned weather data, accumulated into months and split into yearly file."""

    def __init__(self, template, year1, regionvar, variable):
        super(MonthlyBinnedWeatherReader, self).__init__(template, year1, variable)
        self.time_units = 'yyyy0mm'
        self.regionvar = regionvar
        self.bin_limits = netcdfs.readncdf_single(self.file_for_year(year1), 'bin_edges')

    def get_times(self):
        times = []

        # Look for available yearly files
        for year in self.get_years():
            times.extend(year * 1000 + np.arange(1, 13))

        return times

    def get_dimension(self):
        return [self.variable + '-' + str(self.bin_limits[bb-1]) + '-' + str(self.bin_limits[bb]) for bb in range(1, len(self.bin_limits))] # if bin_limits = 2, single value

    def read_iterator(self):
        # Yield data in yearly chunks
        for filename in self.file_iterator():
            ds = xr.open_dataset(filename)
            ds.rename({self.regionvar: 'region'}, inplace=True)
            ds = ds.transpose('time', 'region', 'bin') # Some old code may depend on T x REGIONS x K
            yield ds

    def read_year(self, year):
        ds = xr.open_dataset(self.file_for_year(year))
        ds.rename({self.regionvar: 'region'}, inplace=True)
        ds = ds.transpose('time', 'region', 'bin') # Some old code may depend on T x REGIONS x K
        return ds

class YearlyBinnedWeatherReader(YearlySplitWeatherReader):
    """Exposes binned weather data, accumulated into years from a month binned file."""

    def __init__(self, template, year1, variable):
        super(YearlyBinnedWeatherReader, self).__init__(template, year1, variable)
        self.time_units = 'yyyy000'
        self.monthlyreader = MonthlyBinnedWeatherReader(template, year1, variable)
        self.bin_limits = self.monthlyreader.bin_limits

    def get_times(self):
        return self.get_years()

    def get_dimension(self):
        return self.monthlyreader.get_dimension()

    def read_iterator(self):
        # Yield data summed across years
        for ds in self.monthlyreader.read_iterator():
            ds = ds.groupby('time.year').sum()
            yield ds.rename({'year': 'time'})

    def read_year(self, year):
        ds = self.monthlyreader.read_year(year)
        ds = ds.groupby('time.year').sum()
        return ds.rename({'year': 'time'})

