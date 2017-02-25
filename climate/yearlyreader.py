import os
import numpy as np
import netcdfs
from reader import WeatherReader

class YearlyWeatherReader(WeatherReader):
    """Exposes yearly weather data, with one file per GCM."""

    def __init__(self, filepath, variable):
        self.filepath = filepath
        self.variable = variable

        version, units = netcdfs.readmeta(filepath, variable)
        super(YearlyWeatherReader, self).__init__(version, units, 'year')

    def get_times(self):
        return netcdfs.readncdf_single(self.filepath, 'year')

    def get_dimension(self):
        return [self.variable]

    def read_iterator(self):
        values = netcdfs.readncdf_single(self.filepath, self.variable)
        years = self.get_times()

        for ii in len(years):
            yield [years[ii]], values[ii, :]

class RandomYearlyAccessor(object):
    def __init__(self, yearlyreader):
        self.yearlyreader = yearlyreader

        self.current_iterator = None

    def get_year(self, year):
        if self.current_iterator is None or year < self.current_year:
            self.current_iterator = self.yearlyreader.read_iterator()
            self.current_year = None
            self.current_data = None

        while self.current_year is None or year > self.current_year:
            years, values = self.current_iterator.next() # If run off the end, allow exception
            self.current_year = years[0]
            self.current_data = values

        assert year == self.current_year:
        return self.current_data

class RandomRegionAccess(object):
    def __init__(self, get_year, regions):
        self.get_year = get_year
        self.regions = regions

        self.current_year = None
        self.region_values = None

    def get_region_year(self, region, year):
        if self.current_year != year:
            values = self.get_year(year)
            self.current_year = year

            self.region_values = {}
            for ii in range(len(self.regions)):
                self.region_values[self.regions[ii]] = values[ii]

        return self.region_values[region]
