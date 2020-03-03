"""Classes for exposing weather data available at an annual timestep."""

import os
import numpy as np
import pandas as pd
import xarray as xr
from . import netcdfs
from .reader import WeatherReader, YearlySplitWeatherReader

class YearlyWeatherReader(WeatherReader):
    """Exposes yearly weather data, with one file per GCM."""

    def __init__(self, filepath, *variables, **kwargs):
        self.filepath = filepath
        self.variables = variables
        self.timevar = kwargs.get('timevar', 'time')

        version, units = netcdfs.readmeta(filepath, variables[0])

        regionvar = kwargs.get('regionvar', 'hierid')
        self.regions = netcdfs.readncdf_single(filepath, regionvar, allow_missing=True) # Is None if organized by SHAPENUM
        super(YearlyWeatherReader, self).__init__(version, units, 'year')

    def get_times(self):
        return netcdfs.readncdf_single(self.filepath, self.timevar)

    def get_years(self):
        return list(self.get_times())

    def get_regions(self):
        """Returns a list of all regions available."""
        return self.regions

    def get_dimension(self):
        return self.variables

    def read_iterator(self):
        ds = xr.open_dataset(self.filepath)
        years = self.get_times()

        for ii in range(len(years)):
            yeards = ds[{self.timevar: ii}]
            if self.timevar != 'time':
                yeards.rename({self.timevar: 'time'}, inplace=True)
                if self.timevar == 'year':
                    yeards['time'] = pd.to_datetime(["%d-01-01" % yeards['time']])
                    for variable in self.variables:
                        yeards[variable] = yeards[variable].expand_dims('time', 0)
            yield yeards

    def read_iterator_to(self, maxyear):
        for ds in self.read_iterator():
            if ds['time.year'][0] >= maxyear:
                return
            yield ds

    def read_year(self, year):
        for ds in self.read_iterator():
            if ds['time.year'][0] == year: # always a single value anyway
                return ds

    def __str__(self):
        return "%s: %s" % (self.filepath, ','.join(self.variables))

class YearlyDayLikeWeatherReader(YearlySplitWeatherReader):
    """Exposes yearly weather data, split into yearly files."""

    def __init__(self, template, year1, regionvar, *variables):
        super(YearlyDayLikeWeatherReader, self).__init__(template, year1, variables)
        self.regionvar = regionvar
        self.regions = netcdfs.readncdf_single(self.find_templated(year1), regionvar, allow_missing=True)

    def get_times(self):
        return self.get_years()

    def get_regions(self):
        """Returns a list of all regions available."""
        return self.regions

    def get_dimension(self):
        return self.variable

    def read_iterator(self):
        # Yield data in yearly chunks
        year = self.year1
        for filename in self.file_iterator():
            yield self.prepare_ds(filename, year)
            year += 1

    def read_year(self, year):
        return self.prepare_ds(self.file_for_year(year), year)

    def prepare_ds(self, filename, year):
        ds = xr.open_dataset(filename)
        ds.rename({self.regionvar: 'region'}, inplace=True)
        ds['time'] = np.array([year])
        ds.set_coords(['time'])
        ds[self.variable[0]] = ds[self.variable[0]].expand_dims('time', 0)
        ds.load() # Collect all data now
        return ds

class RandomYearlyAccess(object):
    def __init__(self, yearlyreader):
        self.yearlyreader = yearlyreader

        self.current_iterator = None

    def get_year(self, year):
        if self.current_iterator is None or year < self.current_year:
            self.current_iterator = self.yearlyreader.read_iterator()
            self.current_year = None
            self.current_ds = None

        while self.current_year is None or year > self.current_year:
            ds = next(self.current_iterator) # If run off the end, allow exception
            self.current_year = ds['time.year'][0]
            self.current_ds = ds

        assert year == self.current_year
        return self.current_ds
