import os
import numpy as np
import xarray as xr
import netcdfs
from reader import WeatherReader

class YearlyWeatherReader(WeatherReader):
    """Exposes yearly weather data, with one file per GCM."""

    def __init__(self, filepath, *variables):
        self.filepath = filepath
        self.variables = variables

        version, units = netcdfs.readmeta(filepath, variables[0])
        super(YearlyWeatherReader, self).__init__(version, units, 'year')

    def get_times(self):
        return netcdfs.readncdf_single(self.filepath, 'year')

    def get_years(self):
        return list(self.get_times())

    def get_dimension(self):
        return self.variable

    def read_iterator(self):
        ds = xr.open_dataset(self.filepath)
        years = self.get_times()

        for ii in range(len(years)):
            yield ds.isel(time=ii)

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
            ds = self.current_iterator.next() # If run off the end, allow exception
            self.current_year = ds['time.year'][0]
            self.current_ds = ds

        assert year == self.current_year
        return self.current_ds
