import os
import netcdfs

class WeatherReader(object):
    """Handles reading from weather files."""

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
    def __init__(self, template, year1, variable):
        self.template = template
        self.year1 = year1
        self.variable = variable

    def get_times(self):
        years = []

        year = self.year1
        while os.path.exists(self.template % (year)):
            years.extend(year * 1000 + np.arange(365))
            year += 1

        return years

    def get_dimension(self):
        return [self.variable]

    def read_iterator(self):
        year = self.year1
        while os.path.exists(self.template % (year)):
            yield netcdfs.readncdf(self.template % (year), self.variable)
            year += 1

class BinnedWeatherReader(WeatherReader):
    def __init__(self, template, year1, variable):
        self.template = template
        self.year1 = year1
        self.variable = variable

    def get_times(self):
        years = []

        year = self.year1
        while os.path.exists(self.template % (year)):
            years.extend(year * 1000 + np.arange(1, 13))
            year += 1

        return years

    def get_dimension(self):
        return [self.variable]

    def read_iterator(self):
        year = self.year1
        while os.path.exists(self.template % (year)):
            times, mmbbrr = netcdfs.readncdf_binned(self.template % (year), self.variable)
            mmrrbb = np.swapaxes(mmbbrr, 1, 2)
            yield times, mmrrbb
            year += 1

if __name__ == '__init__':
    template1 = "/shares/gcp/BCSD/grid2reg/cmip5/historical/CCSM4/tas/tas_day_aggregated_historical_r1i1p1_CCSM4_%d.nc"
    weatherreader1 = DailyWeatherReader(template1, 2006, 'tas')

    print weatherreader1.get_times()[:31]

    for times, weather in weatherreader1.read_iterator():
        print times[:31]
        print weather[1000, :31]

    template2 = "/shares/gcp/BCSD/grid2reg/cmip5/historical/CCSM4/tas/tas_day_aggregated_historical_r1i1p1_CCSM4_%d.nc"
    weatherreader2 = BinnedWeatherReader(template2, 2006, 'tas')

    print weatherreader2.get_times()[:2]

    for times, weather in weatherreader2.read_iterator():
        print times[:2]
        print weather[1000, 0]
