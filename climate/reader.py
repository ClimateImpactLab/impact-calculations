import os
import numpy as np
import netcdfs

class WeatherReader(object):
    """Handles reading from weather files."""

    def __init__(self, version, units):
        self.version = version
        self.units = units

    def get_times(self):
        """Returns a list of all times available."""
        raise NotImplementedError

    def get_dimension(self):
        """Returns a list of length K, describing the number of elements
        describing the weather in each region and time period.
        """
        raise NotImplementedError

    def read_iterator(self):
        """Yields a tuple (times, weathers) in whatever chunks are convenient.

        times should be a numpy array with a single dimension.  Let it have length T.
        weather should be a numpy array of size T x REGIONS [x K]
          the last dimension is optional, if more than one value is returned for each time.
        """
        raise NotImplementedError

class DailyWeatherReader(WeatherReader):
    """Exposes daily weather data, split into yearly files."""

    def __init__(self, template, year1, variable):
        version, units = netcdfs.readmeta(template % (year1), variable)
        super(DailyWeatherReader, self).__init__(version, units)

        self.template = template
        self.year1 = year1
        self.variable = variable        

    def get_times(self):
        years = []

        # Look for available yearly files
        year = self.year1
        while os.path.exists(self.template % (year)):
            years.extend(year * 1000 + np.arange(1, 366))
            year += 1

        return years

    def get_dimension(self):
        return [self.variable]

    def read_iterator(self):
        # Yield data in yearly chunks
        year = self.year1
        while os.path.exists(self.template % (year)):
            yield netcdfs.readncdf(self.template % (year), self.variable)
            year += 1

class BinnedWeatherReader(WeatherReader):
    """Exposes binned weather data, accumulated into months and split into yearly file."""

    def __init__(self, template, year1, variable):
        version, units = netcdfs.readmeta(template % (year1), variable)
        super(BinnedWeatherReader, self).__init__(version, units)

        self.template = template
        self.year1 = year1
        self.variable = variable

    def get_times(self):
        years = []

        # Look for available yearly files
        year = self.year1
        while os.path.exists(self.template % (year)):
            years.extend(year * 1000 + np.arange(1, 13))
            year += 1

        return years

    def get_dimension(self):
        return [self.variable + '-' + str(mm) for mm in range(1, 13)]

    def read_iterator(self):
        # Yield data in yearly chunks
        year = self.year1
        while os.path.exists(self.template % (year)):
            times, mmbbrr = netcdfs.readncdf_binned(self.template % (year), self.variable)
            mmrrbb = np.swapaxes(mmbbrr, 1, 2) # Needs to be in T x REGIONS x K
            yield times, mmrrbb
            year += 1

if __name__ == '__main__':
    # Check the first month of daily values
    print "Reading from the daily weather data files."
    template1 = "/shares/gcp/BCSD/grid2reg/cmip5/historical/CCSM4/tas/tas_day_aggregated_historical_r1i1p1_CCSM4_%d.nc"
    weatherreader1 = DailyWeatherReader(template1, 1981, 'tas')

    print weatherreader1.version, weatherreader1.units
    print weatherreader1.get_dimension()
    print weatherreader1.get_times()[:31]
    for times, weather in weatherreader1.read_iterator():
        print times[:31]
        print weather[:31, 1000]
        break

    # Compare it to the first month of binned values
    print "Reading from the binned data files."
    template2 = "/shares/gcp/BCSD/grid2reg/cmip5_bins/historical/CCSM4/tas/tas_Bindays_aggregated_historical_r1i1p1_CCSM4_%d.nc"
    weatherreader2 = BinnedWeatherReader(template2, 1981, 'DayNumber')

    print weatherreader2.version, weatherreader2.units
    print weatherreader2.get_dimension()
    print weatherreader2.get_times()[:2]
    for times, weather in weatherreader2.read_iterator():
        print times[:2]
        print weather[0, 1000]
        break
