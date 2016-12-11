import os
import netcdfs

class WeatherReader(object):
    """Handles reading from weather files."""

    def __init__(self, version, units, time_units):
        self.version = version
        self.units = units
        self.time_units = time_units

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

class YearlySplitWeatherReader(WeatherReader):
    """Exposes weather data, split into yearly files."""

    def __init__(self, template, year1, variable):
        version, units = netcdfs.readmeta(template % (year1), variable)
        super(YearlySplitWeatherReader, self).__init__(version, units, 'year')

        self.template = template
        self.year1 = year1
        self.variable = variable

    def get_years(self):
        "Returns list of years."

        years = []

        # Look for available yearly files
        year = self.year1
        while os.path.exists(self.template % (year)):
            years.append(year)
            year += 1

        return years

    def file_iterator(self):
        # Yield data in yearly chunks
        year = self.year1
        while os.path.exists(self.template % (year)):
            yield self.template % (year)
            year += 1

    def read_iterator_to(self, maxyear):
        for times, weather in self.read_iterator():
            yield times, weather
            if times[0] % 1000 == maxyear:
                break

    # Random access

    def file_for_year(self, year):
        return self.template % (year)

    def read_year(self, year):
        raise NotImplementedError
