import os
import numpy as np
import netcdfs
from openest.generate.weatherslice import DailyWeatherSlice, MonthlyWeatherSlice, YearlyWeatherSlice
from reader import YearlySplitWeatherReader

class DailyWeatherReader(YearlySplitWeatherReader):
    """Exposes daily weather data, split into yearly files."""

    def __init__(self, template, year1, variable):
        super(DailyWeatherReader, self).__init__(template, year1, variable)
        self.time_units = 'yyyyddd'

    def get_times(self):
        times = []

        # Look for available yearly files
        for year in self.get_years():
            times.extend(year * 1000 + np.arange(1, 366))

        return times

    def get_dimension(self):
        return [self.variable]

    def read_iterator(self):
        # Yield data in yearly chunks
        for filename in self.file_iterator():
            yyyyddd, weather = netcdfs.readncdf(filename, self.variable)
            yield DailyWeatherSlice(yyyyddd, weather)

    def read_year(self, year):
        yyyyddd, weather = netcdfs.readncdf(self.file_for_year(year), self.variable)
        return DailyWeatherSlice(yyyyddd, weather)

class MonthlyBinnedWeatherReader(YearlySplitWeatherReader):
    """Exposes binned weather data, accumulated into months and split into yearly file."""

    def __init__(self, template, year1, variable):
        super(MonthlyBinnedWeatherReader, self).__init__(template, year1, variable)
        self.time_units = 'yyyy0mm'
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
            times, mmbbrr = netcdfs.readncdf_binned(filename, self.variable)
            mmrrbb = np.swapaxes(mmbbrr, 1, 2) # Needs to be in T x REGIONS x K
            yield MonthlyWeatherSlice(times, mmrrbb)

    def read_year(self, year):
        times, mmbbrr = netcdfs.readncdf_binned(self.file_for_year(year), self.variable)
        mmrrbb = np.swapaxes(mmbbrr, 1, 2) # Needs to be in T x REGIONS x K
        return MonthlyWeatherSlice(times, mmrrbb)

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
        for times, mmrrbb in self.monthlyreader.read_iterator():
            yield YearlyWeatherSlice([times[0] / 1000], np.expand_dims(np.sum(mmrrbb, axis=0), axis=0))

    def read_year(self, year):
        times, mmrrbb = self.monthlyreader.read_year(year)
        return YearlyWeatherSlice([times[0] / 1000], np.expand_dims(np.sum(mmrrbb, axis=0), axis=0))

