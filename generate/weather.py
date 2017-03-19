import os, re, csv, traceback
import numpy as np
from netCDF4 import Dataset
from helpers import files
import helpers.header as headre
from climate import netcdfs

def iterate_bundles(iterator_readers):
    """
    Return bundles for each RCP and model.
    """
    for scenario, model, pastreader, futurereader in iterator_readers:
        weatherbundle = UnivariatePastFutureWeatherBundle(pastreader, futurereader, scenario, model)
        yield scenario, model, weatherbundle

def iterate_combined_bundles(*iterators_readers):
    scenmodels = {} # {(scenario, model): [(pastreader, futurereader), ...]}
    for iterator_readers in iterators_readers:
        for scenario, model, pastreader, futurereader in iterator_readers:
            if (scenario, model) not in scenmodels:
                scenmodels[(scenario, model)] = []
            scenmodels[(scenario, model)].append((pastreader, futurereader))

    for scenario, model in scenmodels:
        if len(scenmodels[(scenario, model)]) < len(iterators_readers):
            continue

        weatherbundle = MultivariatePastFutureWeatherBundle(scenmodels[(scenario, model)], scenario, model)
        yield scenario, model, weatherbundle

class WeatherBundle(object):
    """A WeatherBundle object is used to access the values for a single variable
    across years, as provided by a given GCM.

    All instantiated WeatherBundles are subclasses of WeatherBundle.  Subclasses
    must define `is_historical`, `yearbundles`, and `get_years`, as described
    below.
    """

    def __init__(self, scenario, model, hierarchy='hierarchy.csv'):
        self.dependencies = []
        self.scenario = scenario
        self.model = model
        self.hierarchy = hierarchy

    def is_historical(self):
        """Returns True if this data presents historical observations; else False."""
        raise NotImplementedError

    def load_regions(self):
        """Load the rows of hierarchy.csv associated with all known regions."""
        mapping = {} # color to hierid

        with open(files.sharedpath("regions/" + self.hierarchy), 'r') as fp:
            reader = csv.reader(headre.deparse(fp, self.dependencies))
            header = reader.next()
            for row in reader:
                if row[header.index('agglomid')]:
                    mapping[int(row[header.index('agglomid')])] = row[0]

        self.regions = []
        for ii in range(len(mapping)):
            self.regions.append(mapping[ii + 1])

    def load_readermeta(self, reader):
        self.version = reader.version
        self.units = reader.units
        if hasattr(reader, 'dependencies'):
            self.dependencies = reader.dependencies

class ReaderWeatherBundle(WeatherBundle):
    def __init__(self, reader, scenario, model, hierarchy='hierarchy.csv'):
        super(ReaderWeatherBundle, self).__init__(scenario, model, hierarchy)
        self.reader = reader

        self.load_readermeta(reader)
        self.load_regions()

    def get_dimension(self):
        return self.reader.get_dimension()

class DailyWeatherBundle(WeatherBundle):
    def yearbundles(self, maxyear=np.inf):
        """Yields the tuple (yyyyddd, weather) for each year up to `maxyear`.
        Each yield should should produce all and only data for a single year.

        yyyyddd should be a numpy array of length 365, and integer values
        constructed like 2016001 for the first day of 2016.

        weather should be a numpy array of size REGIONS x 365.
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
        for yyyyddd, weather in self.yearbundles(maxyear):
            print int(yyyyddd[0]) / 1000

            regionsums += np.mean(weather, axis=0)
            sumcount += 1

        region_averages = regionsums / sumcount
        for ii in range(len(self.regions)):
            yield self.regions[ii], region_averages[ii]

    def baseline_values(self, maxyear):
        """Yield the list of all weather values up to `maxyear` for each region."""

        # Construct an empty matrix to append to
        if len(self.get_dimension()) == 1:
            regionvalues = np.ndarray((0, len(self.regions)))
        else:
            regionvalues = np.ndarray((0, len(self.regions), len(self.get_dimension())))

        # Append each year
        for yyyyddd, weather in self.yearbundles(maxyear):
            print yyyyddd[0]

            # Stack this year below the previous years
            regionvalues = np.vstack((regionvalues, np.expand_dims(np.mean(weather, axis=0), axis=0)))

        # Yield the entire collection of values for each region
        for ii in range(len(self.regions)):
            yield self.regions[ii], regionvalues[:, ii]

class SingleWeatherBundle(ReaderWeatherBundle, DailyWeatherBundle):
    def is_historical(self):
        return False

    def yearbundles(self, maxyear=np.inf):
        for values in self.reader.read_iterator_to(maxyear):
            yield values

    def get_years(self):
        return self.reader.get_years()

class UnivariatePastFutureWeatherBundle(DailyWeatherBundle):
    def __init__(self, pastreader, futurereader, scenario, model, hierarchy='hierarchy.csv'):
        super(UnivariatePastFutureWeatherBundle, self).__init__(scenario, model, hierarchy)
        self.pastreader = pastreader
        self.futurereader = futurereader

        assert self.pastreader.get_dimension() == self.futurereader.get_dimension()

        self.futureyear1 = min(self.futurereader.get_years())

        self.load_readermeta(futurereader)
        self.load_regions()

    def is_historical(self):
        return False

    def yearbundles(self, maxyear=np.inf):
        for values in self.pastreader.read_iterator_to(min(self.futureyear1, maxyear)):
            if len(values[1].shape) == 1:
                assert values[1].shape[0] == len(self.regions)
            else:
                assert values[1].shape[1] == len(self.regions)
            yield values

        if maxyear > self.futureyear1:
            for values in self.futurereader.read_iterator_to(maxyear):
                assert values[1].shape[1] == len(self.regions)
                yield values

    def get_years(self):
        return np.unique(self.pastreader.get_years() + self.futurereader.get_years())

    def get_dimension(self):
        return self.pastreader.get_dimension()

class MultivariatePastFutureWeatherBundle(DailyWeatherBundle):
    def __init__(self, pastfuturereaders, scenario, model, hierarchy='hierarchy.csv'):
        super(MultivariatePastFutureWeatherBundle, self).__init__(scenario, model, hierarchy)
        self.pastfuturereaders = pastfuturereaders

        onefuturereader = self.pastfuturereaders[0][1]
        self.futureyear1 = min(onefuturereader.get_years())

        self.load_readermeta(onefuturereader)
        self.load_regions()

    def is_historical(self):
        return False

    def yearbundles(self, maxyear=np.inf):
        for year in self.get_years():
            if year == maxyear:
                break

            allweather = None
            for pastreader, futurereader in self.pastfuturereaders:
                try:
                    if year < self.futureyear1:
                        yyyyddd, weather = pastreader.read_year(year)
                    else:
                        yyyyddd, weather = futurereader.read_year(year)
                except:
                    print "Failed to get year", year
                    traceback.print_exc()
                    return # No more!

                if len(weather.shape) == 2:
                    weather = np.expand_dims(weather, axis=2)

                if allweather is None:
                    allweather = weather
                else:
                    allweather = np.concatenate((allweather, weather), axis=2)

            yield yyyyddd, allweather

    def get_years(self):
        return np.unique(self.pastfuturereaders[0][0].get_years() + self.pastfuturereaders[0][1].get_years())

    def get_dimension(self):
        alldims = []
        for  pastreader, futurereader in self.pastfuturereaders:
            alldims.extend(pastreader.get_dimension())

        return alldims

    def get_subset(self, index):
        return UnivariatePastFutureWeatherBundle(*self.pastfuturereaders[index], scenario=self.scenario, model=self.model)

class MultivariateHistoricalWeatherBundle2(DailyWeatherBundle):
    """Quick fix, since MultivariateHistoricalWeatherBundle doesn't work with list."""
    def __init__(self, pastreaders, futureyear_end, seed, scenario, model, hierarchy='hierarchy.csv'):
        super(MultivariateHistoricalWeatherBundle2, self).__init__(scenario, model, hierarchy)
        self.pastreaders = pastreaders
        self.seed = seed # Save for get_subset

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
            choices = range(self.pastyear_start, self.pastyear_end + 1)
            self.pastyears = np.random.choice(choices, self.futureyear_end - self.pastyear_start + 1)

        self.load_readermeta(onereader)
        self.load_regions()

    def is_historical(self):
        return True

    def yearbundles(self, maxyear=np.inf):
        year = self.pastyear_start
        for pastyear in self.pastyears:
            allweather = None
            for pastreader in self.pastreaders:
                yyyyddd, weather = pastreader.read_year(pastyear)

                if len(weather.shape) == 2:
                    weather = np.expand_dims(weather, axis=2)

                if allweather is None:
                    allweather = weather
                else:
                    allweather = np.concatenate((allweather, weather), axis=2)

            if yyyyddd[0] > 10000:
                yield (1000 * year) + (yyyyddd % 1000), allweather
            else:
                yield [year], allweather
            year += 1

    def get_years(self):
        return range(int(self.pastyear_start), int(self.futureyear_end) + 1)

    def get_dimension(self):
        alldims = []
        for pastreader in self.pastreaders:
            alldims.extend(pastreader.get_dimension())

        return alldims

    def get_subset(self, index):
        return RepeatedHistoricalWeatherBundle(self.pastreaders[index], self.futureyear_end, self.seed, self.scenario, self.model)

class RepeatedHistoricalWeatherBundle(DailyWeatherBundle):
    def __init__(self, reader, futureyear_end, seed, scenario, model, hierarchy='hierarchy.csv'):
        super(RepeatedHistoricalWeatherBundle, self).__init__(scenario, model, hierarchy)

        self.reader = reader

        years = reader.get_years()
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

        self.load_readermeta(reader)
        self.load_regions()

    def is_historical(self):
        return True

    @staticmethod
    def make_historical(weatherbundle, seed):
        futureyear_end = weatherbundle.get_years()[-1]
        if isinstance(weatherbundle, MultivariatePastFutureWeatherBundle):
            pastreaders = [pastreader for pastreader, futurereader in weatherbundle.pastfuturereaders]
            return MultivariateHistoricalWeatherBundle2(pastreaders, futureyear_end, seed, weatherbundle.scenario, weatherbundle.model)
        else:
            return RepeatedHistoricalWeatherBundle(weatherbundle.pastreader, futureyear_end, seed, weatherbundle.scenario, weatherbundle.model)

    def yearbundles(self, maxyear=np.inf):
        year = self.pastyear_start
        for pastyear in self.pastyears:
            yyyyddd, weather = self.reader.read_year(pastyear)
            if yyyyddd[0] > 10000:
                yield (1000 * year) + (yyyyddd % 1000), weather
            else:
                yield [year], weather
            year += 1

    def get_years(self):
        return range(int(self.pastyear_start), int(self.futureyear_end) + 1)

    def get_dimension(self):
        return self.reader.get_dimension()

class MultivariateHistoricalWeatherBundle(DailyWeatherBundle):
    def __init__(self, template, year_start, year_end, variables, scenario, model,
                 hierarchy='hierarchy.csv', readncdf=netcdfs.readncdf):
        super(MultivariateHistoricalWeatherBundle, self).__init__(scenario, model, hierarchy)

        self.template = template
        self.year_start = year_start
        self.year_end = year_end
        self.variables = variables
        self.readncdf = readncdf

        self.load_regions()
        self.load_metainfo(self.template.format(variables[0], self.year_start), variables[0])

    def is_historical(self):
        return True

    def yearbundles(self, maxyear=np.inf):
        for year in self.get_years():
            masteryyyyddd = None
            weathers = []
            for variable in self.variables:
                yyyyddd, weather = self.readncdf(self.template.format(variable, year), variable)
                if masteryyyyddd is None:
                    masteryyyyddd = yyyyddd
                else:
                    assert np.all(masteryyyyddd == yyyyddd)

                weathers.append(weather)

            yield masteryyyyddd, weathers

    def get_years(self):
        return range(int(self.year_start), int(self.year_end) + 1)

    def baseline_average(self, maxyear):
        """Yield the average weather value up to `maxyear` for each region."""

        regionsums = None
        sumcount = 0
        for yyyyddd, weathers in self.yearbundles(maxyear):
            print int(yyyyddd[0]) / 1000

            if regionsums is None:
                regionsums = [np.mean(weather, axis=0) for weather in weathers]
            else:
                for ii in range(len(weathers)):
                    regionsums[ii] += np.mean(weathers[ii], axis=0)

            sumcount += 1

        region_averages = [regionsum / sumcount for regionsum in regionsums]
        for ii in range(len(self.regions)):
            yield self.regions[ii], [region_averages[jj][ii] for jj in range(len(region_averages))]

if __name__ == '__main__':
    template = "/shares/gcp/BCSD/grid2reg/cmip5/historical/CCSM4/{0}/{0}_day_aggregated_historical_r1i1p1_CCSM4_{1}.nc"
    weatherbundle = MultivariateHistoricalWeatherBundle(template, 1981, 2005, ['pr', 'tas'], 'historical', 'CCSM4')
    yyyyddd, weathers = weatherbundle.yearbundles().next()
    print len(yyyyddd), len(weathers), len(weathers[0]) # 365, 2, 365

    for region, weathers in weatherbundle.baseline_average(2005):
        print region, weathers
        exit()
