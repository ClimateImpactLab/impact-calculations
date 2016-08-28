import os
import numpy as np
import netcdfs
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
            yield netcdfs.readncdf(filename, self.variable)

class BinnedWeatherReader(YearlySplitWeatherReader):
    """Exposes binned weather data, accumulated into months and split into yearly file."""

    def __init__(self, template, year1, variable):
        super(BinnedWeatherReader, self).__init__(template, year1, variable)
        self.time_units = 'yyyyddd'

    def get_times(self):
        times = []

        # Look for available yearly files
        for year in self.get_years():
            times.extend(year * 1000 + np.arange(1, 13))

        return times

    def get_dimension(self):
        return [self.variable + '-' + str(mm) for mm in range(1, 13)]

    def read_iterator(self):
        # Yield data in yearly chunks
        for filename in self.file_iterator():
            times, mmbbrr = netcdfs.readncdf_binned(filename, self.variable)
            mmrrbb = np.swapaxes(mmbbrr, 1, 2) # Needs to be in T x REGIONS x K
            yield times, mmrrbb
            year += 1
