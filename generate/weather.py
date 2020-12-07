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
        transformer = RollingYearTransformer(config['rolling-years'])
    else:
        transformer = WeatherTransformer()

    print("Loading weather...")
        
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

    def load_regions(self, reader=None):
        """Load the rows of hierarchy.csv associated with all known regions."""
        if reader is not None:
            try:
                self.regions = list(reader.get_regions())
                if not isinstance(self.regions[0], str) and np.issubdtype(self.regions[0], np.integer):
                    self.regions = irregions.load_regions(self.hierarchy, self.dependencies)
            except Exception as ex:
                print("Exception but still doing stuff:")
                print(ex)
                print("WARNING: failure to read regions for " + str(reader.__class__))
                self.regions = irregions.load_regions(self.hierarchy, self.dependencies)
        else:
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
    def yearbundles(self, maxyear=np.inf, variable_ofinterest=None):
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
            print(weatherslice.get_years()[0])

            regionsums += np.mean(weatherslice.weathers, axis=0)
            sumcount += 1

        region_averages = regionsums / sumcount
        for ii in range(len(self.regions)):
            yield self.regions[ii], region_averages[ii]

    def baseline_values(self, maxyear, do_mean=True, quiet=False, only_region=None):
        """Yield the list of all weather values up to `maxyear` for each region."""

        if not hasattr(self, 'saved_baseline_values'):
            # Construct an empty dataset to append to
            allds = []

            # Append each year
            for year, ds in self.yearbundles(maxyear):
                if not quiet:
                    print(year)

                # Stack this year below the previous years
                if do_mean:
                    allds.append(ds.mean('time'))
                else:
                    allds.append(ds)

            if isinstance(allds[0], fast_dataset.FastDataset):
                self.saved_baseline_values = fast_dataset.concat(allds, dim='time')
            else:
                self.saved_baseline_values = xr.concat(allds, dim='time') # slower but more reliable

        # Yield the entire collection of values for each region
        if only_region is not None:
            yield only_region, self.saved_baseline_values.sel(region=only_region)
        else:
            for ii in range(len(self.regions)):
                yield self.regions[ii], self.saved_baseline_values.sel(region=self.regions[ii])

class SingleWeatherBundle(ReaderWeatherBundle, DailyWeatherBundle):
    def is_historical(self):
        return False

    def yearbundles(self, maxyear=np.inf, variable_ofinterest=None):
        for year, ds in self.reader.read_iterator_to(maxyear):
            for year2, ds2 in self.transformer.push(year, ds):
                yield year2, ds2

    def get_years(self):
        return self.transformer.get_years(self.reader.get_years())

class PastFutureWeatherBundle(DailyWeatherBundle):
    def __init__(self, pastfuturereaders, scenario, model, hierarchy='hierarchy.csv', transformer=WeatherTransformer()):
        super(PastFutureWeatherBundle, self).__init__(scenario, model, hierarchy, transformer)
        self.pastfuturereaders = pastfuturereaders

        self.variable2readers = {}
        for pastfuturereader in pastfuturereaders:
            assert pastfuturereader[0].get_dimension() == pastfuturereader[1].get_dimension()
            for variable in pastfuturereader[0].get_dimension():
                if variable not in self.variable2readers:
                    self.variable2readers[variable] = pastfuturereader
                else:
                    self.variable2readers[variable] = None # ambiguous-- don't provide shortcut
                    print("WARNING: Multiple weather readers provide " + variable)
                    
        onefuturereader = self.pastfuturereaders[0][1]
        self.futureyear1 = min(onefuturereader.get_years())

        self.load_readermeta(onefuturereader)
        self.load_regions(onefuturereader)

    def is_historical(self):
        return False

    def yearbundles(self, maxyear=np.inf, variable_ofinterest=None):
        """Yields xarray Datasets for each year up to (but not including) `maxyear`"""
        if len(self.pastfuturereaders) == 1:
            year = None # In case no additional years in pastreader
            for ds in self.pastfuturereaders[0][0].read_iterator_to(min(self.futureyear1, maxyear)):
                assert ds.region.shape[0] == len(self.regions), "Region length mismatch: %d <> %d" % (ds.region.shape[0], len(self.regions))
                year = ds['time.year'][0]
                year = int(year.values) if isinstance(year, xr.DataArray) else int(year)
                for year2, ds2 in self.transformer.push(year, ds):
                    yield year2, ds2

            if year is None:
                lastyear = self.futureyear1 - 1
            else:
                lastyear = year
            if maxyear > self.futureyear1:
                for ds in self.pastfuturereaders[0][1].read_iterator_to(maxyear):
                    year = ds['time.year'][0]
                    year = int(year.values) if isinstance(year, xr.DataArray) else int(year)
                    if year <= lastyear:
                        continue # allow for overlapping weather
                    assert ds.region.shape[0] == len(self.regions), "Region length mismatch: %d <> %d" % (ds.region.shape[0], len(self.regions))
                    for year2, ds2 in self.transformer.push(year, ds):
                        yield year2, ds2
            return

        # Set this here so it's not called in nested for-loops.
        # Legacy behavior is to suppress Exceptions raised when
        # reading climate data below. This can create NaNs in
        # projection output. Work around is to set 'IMPERICS_ALLOW_IOEXCEPTIONS'
        # environment variable to "1", allowing IO exceptions to raise and
        # halt execution with error message.
        allow_ioexceptions = int(os.environ.get("IMPERICS_ALLOW_IOEXCEPTIONS", "0"))

        for year in self.get_reader_years():
            if year == maxyear:
                break

            allds = xr.Dataset({'region': self.regions})

            for pastreader, futurereader in self.pastfuturereaders:
                if variable_ofinterest and self.variable2readers.get(variable_ofinterest) != (pastreader, futurereader):
                    continue # skip this
                
                try:
                    if year < self.futureyear1:
                        ds = pastreader.read_year(year)
                    else:
                        ds = futurereader.read_year(year)
                except Exception as ex:
                    if allow_ioexceptions:
                        raise ex
                    else:
                        # Legacy behavior continues execution despite exception
                        print("Got exception but returning:")
                        print(ex)
                        print("Failed to get year", year)
                        traceback.print_exc()
                        return # No more!

                assert ds.region.shape[0] == len(self.regions)
                allds = fast_dataset.merge((allds, ds)) #xr.merge((allds, ds))

            for year2, ds2 in self.transformer.push(year, allds):
                yield year2, ds2

    def get_reader_years(self):
        return np.unique(self.pastfuturereaders[0][0].get_years() + self.pastfuturereaders[0][1].get_years())

    def get_years(self):
        return self.transformer.get_years(self.get_reader_years())

    def get_dimension(self):
        alldims = []
        for  pastreader, futurereader in self.pastfuturereaders:
            alldims.extend(pastreader.get_dimension())

        return alldims

class HistoricalWeatherBundle(DailyWeatherBundle):
    """WeatherBundle composed of randomly or sequentially drawn historical weather

    Parameters
    ----------
    pastreaders : Sequence of climate.reader.WeatherReader
        Sequence of WeatherReader populated with historical weather data to
        sample.
    futureyear_end : int
        Year in the future to randomly sample to. Random weather events are
        drawn to extend from the last year in `pastreaders` to this year.
    seed : int or None
        Seed for RNG when randomly sampling from historical weather record.
        If `None`, then cycles in year order.
    scenario : str
        The Representative Concentration Pathway name, e.g. ``"rcp85"``.
    model : str
        Climate model name, e.g. ``"CCSM4"``.
    hierarchy : str, optional
        Path to CSV file of regional hierarchy or "hierids".
    transformer : generate.weather.WeatherTransformer, optional
        Transformer to apply to the bundled weather Datasets.
    pastyear_end : int or None
        Latest year to use when constructing historical baseline.
    """
    def __init__(self, pastreaders, futureyear_end, seed, scenario, model, hierarchy='hierarchy.csv', transformer=WeatherTransformer(), pastyear_end=None):
        super(HistoricalWeatherBundle, self).__init__(scenario, model, hierarchy, transformer)
        self.pastreaders = pastreaders

        onereader = self.pastreaders[0]
        years = onereader.get_years()
        self.pastyear_start = min(years)
        if pastyear_end is None:
            self.pastyear_end = max(years)
        else:
            self.pastyear_end = pastyear_end
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
            choices = list(range(int(self.pastyear_start), int(self.pastyear_end) + 1))
            self.pastyears = np.random.choice(choices, int(self.futureyear_end - self.pastyear_start + 1))

        self.load_readermeta(onereader)
        self.load_regions(onereader)

    def is_historical(self):
        return True

    def yearbundles(self, maxyear=np.inf, variable_ofinterest=None):
        """Generator yielding per-year weather xr.Datasets

        Parameters
        ----------
        maxyear : int, optional
        variable_ofinterest : str or None, optional

        Yields
        ------
        int
            Year of dataset
        xr.Dataset
            Dataset of weather values
        """
        year = self.pastyear_start

        if len(self.pastreaders) == 1:
            for pastyear in self.pastyears:
                if year > maxyear:
                    break

                ds = self.pastreaders[0].read_year(pastyear)
                ds = self.update_year(ds, pastyear, year)
                
                for year2, ds2 in self.transformer.push(year, ds):
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

            allds = self.update_year(allds, pastyear, year)
                
            for year2, ds2 in self.transformer.push(year, allds):
                yield year2, ds2
            year += 1

    def update_year(self, ds, pastyear, futureyear):
        """Corrects resampled weather Dataset 'time' coordinate to a new range

        Parameters
        ----------
        ds : xr.Dataset
            Weather data with 'time' coordinate.
        pastyear : int
        futureyear : int

        Returns
        -------
        xr.Dataset
        """
        # Correct the time - should generalize
        if isinstance(ds['time'][0], np.datetime64):
            ds['time']._values = np.array([str(futureyear) + str(date)[4:] for date in ds['time']._values])
        elif ds['time'][0] < 10000:
            ds['time']._values += futureyear - pastyear # YYYY
        elif ds['time'][0] < 1000000:
            ds['time']._values += (futureyear - pastyear) * 100 # YYYYMM
        else:
            ds['time']._values += (futureyear - pastyear) * 1000 # YYYYDDD
        return ds
            
    def get_years(self):
        """Get list of years represented in this bundle"""
        return self.transformer.get_years(list(range(int(self.pastyear_start), int(self.futureyear_end) + 1)))

    def get_dimension(self):
        alldims = []
        for pastreader in self.pastreaders:
            alldims.extend(pastreader.get_dimension())

        return alldims

    @staticmethod
    def make_historical(weatherbundle, seed, pastyear_end=None):
        """Sugar to easily instantiate a HistoricalWeatherBundle from a PastFutureWeatherBundle

        Parameters
        ----------
        weatherbundle : generate.weather.PastFutureWeatherBundle
            Weatherbundle to resample.
        seed : int
            Seed for RNG.

        Returns
        -------
        HistoricalWeatherBundle
        """
        futureyear_end = max(weatherbundle.get_reader_years())
        pastreaders = [pastreader for pastreader, futurereader in weatherbundle.pastfuturereaders]
        return HistoricalWeatherBundle(pastreaders, futureyear_end, seed, weatherbundle.scenario, weatherbundle.model, transformer=weatherbundle.transformer, pastyear_end=pastyear_end)

class AmorphousWeatherBundle(WeatherBundle):
    def __init__(self, pastfuturereader_dict, scenario, model, hierarchy='hierarchy.csv', transformer=WeatherTransformer()):
        super(AmorphousWeatherBundle, self).__init__(scenario, model, hierarchy, transformer)

        self.pastfuturereader_dict = pastfuturereader_dict
        
    def get_concrete(self, names):
        pastfuturereaders = [self.pastfuturereader_dict[name] for name in names]
        return PastFutureWeatherBundle(pastfuturereaders, self.scenario, self.model)

class RollingYearTransformer(WeatherTransformer):
    """WeatherTransformer giving years and weather for a number of past years

    Parameters
    ----------
    rolling_years : int, optional
        Number of previous years to include in output transformation. Must be
        > 1.
    """
    def __init__(self, rolling_years=1):
        self.rolling_years = rolling_years
        assert self.rolling_years > 1
        self.pastdses = []
        self.last_year = None

    def get_years(self, years):
        """Get rolling years from 'years' sequence"""
        return years[:-self.rolling_years + 1]
        
    def push(self, year, ds):
        """Yield transformed year(s) and Dataset(s) for year and Dataset

        Parameters
        ----------
        year : int
            Input year to transform.
        ds : xarray.Dataset
            Dataset of weather. Assumed to have a "time" dim.

        Yields
        ------
        int
            Transformed year.
        xarray.Dataset
            Weather data for transformed year.
        """
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

