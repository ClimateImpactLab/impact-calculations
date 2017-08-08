import os, glob
import numpy as np
import xarray as xr
import netcdfs
from datastore import irregions

class WeatherReader(object):
    """Handles reading from weather files."""

    def __init__(self, version, units, time_units):
        self.version = version
        self.units = units
        self.time_units = time_units

    def get_times(self):
        """Returns a list of all times available."""
        raise NotImplementedError

    def get_regions(self):
        """Returns a list of all regions available."""
        raise NotImplementedError
    
    def get_dimension(self):
        """Returns a list of length K, describing the number of elements
        describing the weather in each region and time period.
        """
        raise NotImplementedError

    def read_iterator(self):
        """Yields an xarray Dataset in whatever chunks are convenient.
        """
        raise NotImplementedError

class YearlySplitWeatherReader(WeatherReader):
    """Exposes weather data, split into yearly files."""

    def __init__(self, template, year1, variable):
        self.template = template

        if isinstance(variable, list) or isinstance(variable, tuple):
            version, units = netcdfs.readmeta(self.find_templated(year1), variable[0])
        else:
            version, units = netcdfs.readmeta(self.find_templated(year1), variable)
            
        super(YearlySplitWeatherReader, self).__init__(version, units, 'year')
            
        self.year1 = year1
        self.variable = variable

    def get_years(self):
        "Returns list of years."

        years = []

        # Look for available yearly files
        year = self.year1
        while os.path.exists(self.find_templated(year)):
            years.append(year)
            year += 1

        return years

    def file_iterator(self):
        # Yield data in yearly chunks
        year = self.year1
        while os.path.exists(self.find_templated(year)):
            yield self.find_templated(year)
            year += 1

    def read_iterator_to(self, maxyear):
        for ds in self.read_iterator():
            yield ds
            if ds['time.year'][0] >= maxyear:
                break

    # Random access

    def file_for_year(self, year):
        return self.find_templated(year)

    def read_year(self, year):
        """Return the xarray Dataset for a given year."""
        raise NotImplementedError

    # Template handling

    def find_templated(self, year):
        if "%v" not in self.template:
            return self.template % (year)

        options = glob.glob(self.template.replace("%v", "*") % (year))
        if len(options) == 0:
            return self.template.replace("%v", "unknown") % (year)
        
        options = map(lambda s: os.path.splitext(os.path.basename(s))[0], options)
        options.sort(key=lambda s: map(int, s.split('.')))
        return self.template.replace("%v", options[-1]) % (year)
    
class ConversionWeatherReader(WeatherReader):
    """Wraps another weather reader, applying conversion to its weather."""

    def __init__(self, reader, time_conversion, ds_conversion):
        super(ConversionWeatherReader, self).__init__(reader.version, reader.units, reader.time_units)
        self.reader = reader
        self.time_conversion = time_conversion
        self.ds_conversion = ds_conversion

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
        """Yields an xarray Dataset in whatever chunks are convenient.
        """
        for ds in self.reader.read_iterator():
            yield self.ds_conversion(ds)

    def read_year(self, year):
        return self.ds_conversion(self.reader.read_year(year))

class RegionReorderWeatherReader(WeatherReader):
    """Wraps another weather reader, reordering its regions to IR shapefile order."""

    def __init__(self, reader, hierarchy='hierarchy.csv'):
        super(RegionReorderWeatherReader, self).__init__(reader.version, reader.units, reader.time_units)
        self.reader = reader

        self.dependencies = []
        desired_regions = irregions.load_regions(hierarchy, self.dependencies)
        observed_regions = self.reader.get_regions()

        mapping = {} ## mapping maps from region to index in observed_regions
        for ii in range(len(observed_regions)):
            mapping[''.join(observed_regions[ii])] = ii

        self.reorder = np.array([mapping[region] for region in desired_regions])

    def get_times(self):
        """Returns a list of all times available."""
        return self.reader.get_times()

    def get_years(self):
        return self.reader.get_years()

    def get_dimension(self):
        """Returns a list of length K, describing the number of elements
        describing the weather in each region and time period."""
        return self.reader.get_dimension()

    def read_iterator(self):
        """Yields an xarray Dataset in whatever chunks are convenient."""
        for ds in self.reader.read_iterator():
            yield self.reorder_regions(ds)

    def read_year(self, year):
        ds = self.reader.read_year(year)
        return self.reorder_regions(ds)
        
    def reorder_regions(self, ds):
        newds = xr.Dataset({'time': ds.time, 'region': ds.region[self.reorder]})
        for var in ds:
            if var in ['time', 'region']:
                continue
            newds[var] = ds[var] # Automatically reordered

        return newds
