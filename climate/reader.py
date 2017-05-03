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
        """Yields a WeatherSlice in whatever chunks are convenient.
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
        for weatherslice in self.read_iterator():
            yield weatherslice
            if weatherslice.get_years()[0] >= maxyear:
                break

    # Random access

    def file_for_year(self, year):
        return self.template % (year)

    def read_year(self, year):
        raise NotImplementedError

class ConversionWeatherReader(WeatherReader):
    """Wraps another weather reader, applying conversion to its weatherslices."""

    def __init__(self, reader, time_conversion, weatherslice_conversion):
        super(ConversionWeatherReader, self).__init__(reader.version, reader.units, reader.time_units)
        self.reader = reader
        self.time_conversion = time_conversion
        self.weatherslice_conversion = weatherslice_conversion

    def get_times(self):
        """Returns a list of all times available."""
        return self.time_conversion(self.reader.get_times())

    def get_years(self):
        return list(self.get_times()) # for now, assume converted to years
        
    def get_dimension(self):
        """Returns a list of length K, describing the number of elements
        describing the weather in each region and time period.
        """
        return self.reader.get_dimension()

    def read_iterator(self):
        """Yields a WeatherSlice in whatever chunks are convenient.
        """
        for weatherslice in self.read_iterator():
            yield self.weatherslice_conversion(weatherslice)

    def read_year(self, year):
        return self.weatherslice_conversion(self.reader.read_year(year))
