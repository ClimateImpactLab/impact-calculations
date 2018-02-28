import os, re, csv, traceback
import numpy as np
import xarray as xr
from netCDF4 import Dataset
from impactlab_tools.utils import files
from openest.generate import fast_dataset
import helpers.header as headre
from climate import netcdfs
from datastore import irregions

class WeatherTransformer(object):
    def push(self, year, ds):
        yield year, ds

    def get_years(self, years):
        return years

def iterate_bundles(*iterators_readers, **config):
    """
    Return bundles for each RCP and model.
    """
    if 'rolling-years' in config:
        transformer = RollingYearTransfomer(config['rolling-years'])
    else:
        transformer = WeatherTransformer()

    if len(iterators_readers) == 1:
        for scenario, model, pastreader, futurereader in iterators_readers[0]:
            if 'gcm' in config and config['gcm'] != model:
                continue
            weatherbundle = PastFutureWeatherBundle([(pastreader, futurereader)], scenario, model, transformer=transformer)
            yield scenario, model, weatherbundle
        return
    
    scenmodels = {} # {(scenario, model): [(pastreader, futurereader), ...]}
    for iterator_readers in iterators_readers:
        for scenario, model, pastreader, futurereader in iterator_readers:
            if 'gcm' in config and config['gcm'] != model:
                continue
            if (scenario, model) not in scenmodels:
                scenmodels[(scenario, model)] = []
            scenmodels[(scenario, model)].append((pastreader, futurereader))

    for scenario, model in scenmodels:
        if len(scenmodels[(scenario, model)]) < len(iterators_readers):
            continue

        weatherbundle = PastFutureWeatherBundle(scenmodels[(scenario, model)], scenario, model, transformer=transformer)
        yield scenario, model, weatherbundle

def iterate_amorphous_bundles(iterators_reader_dict):
    scenmodels = {} # {(scenario, model): [(pastreader, futurereader), ...]}
    for name in iterators_reader_dict:
        for scenario, model, pastreader, futurereader in iterators_reader_dict[name]:
            if (scenario, model) not in scenmodels:
                scenmodels[(scenario, model)] = {}
            scenmodels[(scenario, model)][name] = (pastreader, futurereader)

    for scenario, model in scenmodels:
        if len(scenmodels[(scenario, model)]) < len(iterators_reader_dict):
            continue

        weatherbundle = AmorphousWeatherBundle(scenmodels[(scenario, model)], scenario, model)
        yield scenario, model, weatherbundle

def get_weatherbundle(only_scenario, only_model, iterators_readers):
    for scenario, model, weatherbundle in iterate_bundles(*iterators_readers):
        if scenario == only_scenario and model == only_model:
            return weatherbundle
        
class WeatherBundle(object):
    """A WeatherBundle object is used to access the values for a single variable
    across years, as provided by a given GCM.

    All instantiated WeatherBundles are subclasses of WeatherBundle.  Subclasses
    must define `is_historical`, `yearbundles`, and `get_years`, as described
    below.
    """

    def __init__(self, scenario, model, hierarchy='hierarchy.csv', transformer=WeatherTransformer()):
        self.dependencies = []
        self.scenario = scenario
        self.model = model
        self.hierarchy = hierarchy
        self.transformer = transformer

    def is_historical(self):
        """Returns True if this data presents historical observations; else False."""
        raise NotImplementedError

    def load_regions(self):
        """Load the rows of hierarchy.csv associated with all known regions."""
        self.regions = irregions.load_regions(self.hierarchy, self.dependencies)

    def load_readermeta(self, reader):
        self.version = reader.version
        self.units = reader.units
        if hasattr(reader, 'dependencies'):
            self.dependencies = reader.dependencies

class ReaderWeatherBundle(WeatherBundle):
    def __init__(self, reader, scenario, model, hierarchy='hierarchy.csv', transformer=WeatherTransformer()):
        super(ReaderWeatherBundle, self).__init__(scenario, model, hierarchy, transformer)
        self.reader = reader

        self.load_readermeta(reader)
        self.load_regions()

    def get_dimension(self):
        return self.reader.get_dimension()

class DailyWeatherBundle(WeatherBundle):
    def yearbundles(self, maxyear=np.inf):
        """Yields a tuple of (year, xarray Dataset) for each year up to `maxyear`.
        Each yield should should produce all and only data for a single year.
        """
        raise NotImplementedError

    def get_years(self):
        """Returns a list of all years available for the given WeatherBundle."""
        raise NotImplementedError

    def get_dimension(self):
        """Return a list of the values for each period x region."""
        raise NotImplementedError

    def baseline_average(self, maxyear):
        """Yield the average weather value up to `maxyear` for each region."""

        if len(self.get_dimension()) == 1:
            regionsums = np.zeros(len(self.regions))
        else:
            regionsums = np.zeros((len(self.regions), len(self.get_dimension())))

        sumcount = 0
        for weatherslice in self.yearbundles(maxyear):
            print weatherslice.get_years()[0]

            regionsums += np.mean(weatherslice.weathers, axis=0)
            sumcount += 1

        region_averages = regionsums / sumcount
        for ii in range(len(self.regions)):
            yield self.regions[ii], region_averages[ii]

    def baseline_values(self, maxyear, do_mean=True):
        """Yield the list of all weather values up to `maxyear` for each region."""

        # Construct an empty dataset to append to
        allds = []

        # Append each year
        for year, ds in self.yearbundles(maxyear):
            print year

            # Stack this year below the previous years
            if do_mean:
                allds.append(ds.mean('time'))
            else:
                allds.append(ds)

        allyears = fast_dataset.concat(allds, dim='time')

        # Yield the entire collection of values for each region
        for ii in range(len(self.regions)):
            yield self.regions[ii], allyears.sel(region=self.regions[ii])

class SingleWeatherBundle(ReaderWeatherBundle, DailyWeatherBundle):
    def is_historical(self):
        return False

    def yearbundles(self, maxyear=np.inf):
        for year, ds in self.reader.read_iterator_to(maxyear):
            for year2, ds2 in self.transformer.push(year, ds):
                yield year2, ds2

    def get_years(self):
        return self.transformer.get_years(self.reader.get_years())

class PastFutureWeatherBundle(DailyWeatherBundle):
    def __init__(self, pastfuturereaders, scenario, model, hierarchy='hierarchy.csv', transformer=WeatherTransformer()):
        super(PastFutureWeatherBundle, self).__init__(scenario, model, hierarchy, transformer)
        self.pastfuturereaders = pastfuturereaders

        for pastfuturereader in pastfuturereaders:
            assert pastfuturereader[0].get_dimension() == pastfuturereader[1].get_dimension()
        
        onefuturereader = self.pastfuturereaders[0][1]
        self.futureyear1 = min(onefuturereader.get_years())

        self.load_readermeta(onefuturereader)
        self.load_regions()

    def is_historical(self):
        return False

    def yearbundles(self, maxyear=np.inf):
        """Yields xarray Datasets for each year up to (but not including) `maxyear`"""
        if len(self.pastfuturereaders) == 1:
            for ds in self.pastfuturereaders[0][0].read_iterator_to(min(self.futureyear1, maxyear)):
                assert ds.region.shape[0] == len(self.regions)
                year = ds['time.year'][0]
                for year2, ds2 in self.transformer.push(year, ds):
                    yield year2, ds2

            lastyear = year
            if maxyear > self.futureyear1:
                for ds in self.pastfuturereaders[0][1].read_iterator_to(maxyear):
                    year = ds['time.year'][0]
                    if year <= lastyear:
                        continue # allow for overlapping weather
                    assert ds.region.shape[0] == len(self.regions)
                    for year2, ds2 in self.transformer.push(year, ds):
                        yield year2, ds2
            return
        
        for year in self.get_years():
            if year == maxyear:
                break

            allds = xr.Dataset({'region': self.regions})

            for pastreader, futurereader in self.pastfuturereaders:
                try:
                    if year < self.futureyear1:
                        ds = pastreader.read_year(year)
                    else:
                        ds = futurereader.read_year(year)
                except:
                    print "Failed to get year", year
                    traceback.print_exc()
                    return # No more!

                assert ds.region.shape[0] == len(self.regions)
                allds = fast_dataset.merge((allds, ds)) #xr.merge((allds, ds))

            for year2, ds2 in self.transformer.push(year, allds):
                yield year2, ds2

    def get_years(self):
        return self.transformer.get_years(np.unique(self.pastfuturereaders[0][0].get_years() + self.pastfuturereaders[0][1].get_years()))

    def get_dimension(self):
        alldims = []
        for  pastreader, futurereader in self.pastfuturereaders:
            alldims.extend(pastreader.get_dimension())

        return alldims

class HistoricalWeatherBundle(DailyWeatherBundle):
    def __init__(self, pastreaders, futureyear_end, seed, scenario, model, hierarchy='hierarchy.csv', transformer=WeatherTransformer()):
        super(HistoricalWeatherBundle, self).__init__(scenario, model, hierarchy, transformer)
        self.pastreaders = pastreaders

        onereader = self.pastreaders[0]
        years = onereader.get_years()
        self.pastyear_start = min(years)
        self.pastyear_end = max(years)
        self.futureyear_end = futureyear_end

        # Generate the full list of past years
        self.pastyears = []
        if seed is None:
            # Cycle in year order
            year = self.pastyear_start
            pastyear = self.pastyear_start
            dt = 1
            while year <= self.futureyear_end:
                self.pastyears.append(pastyear)
                year += 1
                pastyear += dt
                if pastyear == self.pastyear_end:
                    dt = -1
                if pastyear == self.pastyear_start:
                    dt = 1
        else:
            # Randomly choose years with replacement
            np.random.seed(seed)
            choices = range(int(self.pastyear_start), int(self.pastyear_end) + 1)
            self.pastyears = np.random.choice(choices, int(self.futureyear_end - self.pastyear_start + 1))

        self.load_readermeta(onereader)
        self.load_regions()

    def is_historical(self):
        return True

    def yearbundles(self, maxyear=np.inf):
        year = self.pastyear_start

        if len(self.pastreaders) == 1:
            for pastyear in self.pastyears:
                if year > maxyear:
                    break
                for year2, ds2 in self.transformer.push(year, self.reader.read_year(pastyear)):
                    yield year2, ds2
                year += 1
            return
            
        for pastyear in self.pastyears:
            if year > maxyear:
                break
            allds = xr.Dataset({'region': self.regions})
            for pastreader in self.pastreaders:
                ds = pastreader.read_year(pastyear)
                allds = fast_dataset.merge((allds, ds)) #xr.merge((allds, ds))

            # Correct the time - should generalize
            if allds['time'][0] < 10000:
                allds['time']._values += year - pastyear # YYYY
            elif allds['time'][0] < 1000000:
                allds['time']._values += (year - pastyear) * 100 # YYYYMM
            else:
                allds['time']._values += (year - pastyear) * 1000 # YYYYDDD
                
            for year2, ds2 in self.transformer.push(year, allds):
                yield year2, ds2
            year += 1

    def get_years(self):
        return range(int(self.pastyear_start), int(self.futureyear_end) + 1)

    def get_dimension(self):
        alldims = []
        for pastreader in self.pastreaders:
            alldims.extend(pastreader.get_dimension())

        return alldims

    @staticmethod
    def make_historical(weatherbundle, seed):
        futureyear_end = weatherbundle.get_years()[-1]
        pastreaders = [pastreader for pastreader, futurereader in weatherbundle.pastfuturereaders]
        return HistoricalWeatherBundle(pastreaders, futureyear_end, seed, weatherbundle.scenario, weatherbundle.model)

class AmorphousWeatherBundle(WeatherBundle):
    def __init__(self, pastfuturereader_dict, scenario, model, hierarchy='hierarchy.csv', transformer=WeatherTransformer()):
        super(AmorphousWeatherBundle, self).__init__(scenario, model, hierarchy, transformer)

        self.pastfuturereader_dict = pastfuturereader_dict
        
    def get_concrete(self, names):
        pastfuturereaders = [self.pastfuturereader_dict[name] for name in names]
        return PastFutureWeatherBundle(pastfuturereaders, self.scenario, self.model)

class RollingYearTransfomer(WeatherTransformer):
    def __init__(self, rolling_years=1):
        self.rolling_years = rolling_years
        assert self.rolling_years > 1
        self.pastdses = []
        self.last_year = None

    def get_years(self, years):
        return years[:-self.rolling_years + 1]
        
    def push(self, year, ds):
        if self.last_year is not None and year != self.last_year + 1:
            self.pastdses = []
        self.last_year = year
        
        if len(self.pastdses) < self.rolling_years:
            self.pastdses.append(ds)
        else:
            self.pastdses = self.pastdses[1:] + [ds]

        if len(self.pastdses) == self.rolling_years:
            ds = fast_dataset.concat(self.pastdses, dim='time')
            yield year - self.rolling_years + 1, ds
