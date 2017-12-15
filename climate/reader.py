import os, glob
import numpy as np
import xarray as xr
import pandas as pd
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

    def read_iterator_to(self, maxyear):
        """Yields an xarray Dataset in whatever chunks are convenient to a given year."""
        for ds in self.reader.read_iterator():
            yield self.reorder_regions(ds)
            if ds['time.year'][0] >= maxyear:
                break

    def read_year(self, year):
        ds = self.reader.read_year(year)
        return self.reorder_regions(ds)
        
    def reorder_regions(self, ds):
        newvars = {}
        for var in ds:
            if var in ['time', 'region']:
                continue
            #newds[var] = ds[var] # Automatically reordered
            # Don't use automatic reordering: too slow later (XXX: is this true?)
            if len(ds[var].dims) == 1:
                if 'region' not in ds[var].dims:
                    newvars[var] = ds[var]
                else:
                    newvars[var] = (['region'], ds[var].values[self.reorder])
            else:
                if ds[var].dims.index('time') == 0:
                    newvars[var] = (['time', 'region'], ds[var].values[:, self.reorder])
                else:
                    newvars[var] = (['region', 'time'], ds[var].values[self.reorder, :])

        newds = xr.Dataset(newvars, coords={'time': ds.time, 'region': ds.region[self.reorder]})
        newds.load()

        return newds

class RenameReader(WeatherReader):
    """Wraps another weatherReader, renaming all variables."""
    def __init__(self, reader, renamer):
        super(RenameReader, self).__init__(reader.version, reader.units, reader.time_units)
        self.reader = reader
        self.renamer = renamer

    def get_times(self):
        """Returns a list of all times available."""
        return self.reader.get_times()

    def get_years(self):
        return self.reader.get_years()
        
    def get_dimension(self):
        """Returns a list of length K, describing the number of elements
        describing the weather in each region and time period.
        """
        return map(self.renamer, self.reader.get_dimension())

    def read_iterator(self):
        """Yields an xarray Dataset in whatever chunks are convenient.
        """
        for year in self.get_years():
            yield self.read_year(year)

    def read_year(self, year):
        renames = {name: self.renamer(name) for name in self.reader.get_dimension()}
        
        return self.reader.read_year(year).rename(renames)
    
class HistoricalCycleReader(WeatherReader):
    """Wraps another weather reader, iterating through history repeatedly, pretending to be a future reader."""

    def __init__(self, reader, futurereader):
        super(HistoricalCycleReader, self).__init__(reader.version, reader.units, reader.time_units)
        self.reader = reader
        self.futurereader = futurereader

    def get_times(self):
        """Returns a list of all times available."""
        return self.futurereader.get_times()

    def get_years(self):
        return self.futurereader.get_years()
        
    def get_dimension(self):
        """Returns a list of length K, describing the number of elements
        describing the weather in each region and time period.
        """
        return map(lambda x: x + '.histclim', self.futurereader.get_dimension())

    def read_iterator(self):
        """Yields an xarray Dataset in whatever chunks are convenient.
        """
        for year in self.get_years():
            yield self.read_year(year)

    def read_year(self, year):
        histyears = self.reader.get_years()
        fromstart = (year - histyears[0]) % (2 * len(histyears) - 2)

        renames = {name: name + '.histclim' for name in self.futurereader.get_dimension()}
        
        if fromstart < len(histyears):
            if year <= histyears[-1]:
                return self.reader.read_year(histyears[fromstart]).rename(renames)
            else:
                ds = self.reader.read_year(histyears[fromstart]).rename(renames)
        else:
            ds = self.reader.read_year(histyears[-(fromstart - len(histyears) + 2)]).rename(renames)

        ds['yyyyddd'].values = ds['yyyyddd'].values % 1000 + year * 1000
        ds['time'].values = pd.date_range('%d-01-01' % year, periods=365)
        return ds
