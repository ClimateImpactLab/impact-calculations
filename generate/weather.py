import os, re, csv
import numpy as np
from netCDF4 import Dataset
from helpers import files
import helpers.header as headre
from climate import netcdfs

def iterate_binned_bundles(basedir, readercls):
    """
    Return bundles for each RCP and model.

    basedir points to directory with both 'historical', 'rcp*'
    """
    # Collect the entire complement of models
    models = os.listdir(os.path.join(basedir, 'historical'))

    for scenario in os.listdir(basedir):
        if scenario[0:3] != 'rcp':
            continue

        for model in models:
            pasttemplate = os.path.join(basedir, 'historical', model, 'tas/tas_Bindays_aggregated_historical_r1i1p1_' + model + '_%d.nc')
            futuretemplate = os.path.join(basedir, scenario, model, 'tas/tas_Bindays_aggregated_' + scenario + '_r1i1p1_' + model + '_%d.nc')

            pastreader = readercls(pasttemplate, 1981, 'DayNumber')
            futurereader = readercls(futuretemplate, 2006, 'DayNumber')

            weatherbundle = UnivariatePastFutureWeatherBundle(pastreader, futurereader)
            yield scenario, model, weatherbundle

class WeatherBundle(object):
    """A WeatherBundle object is used to access the values for a single variable
    across years, as provided by a given GCM.

    All instantiated WeatherBundles are subclasses of WeatherBundle.  Subclasses
    must define `is_historical`, `yearbundles`, and `get_years`, as described
    below.
    """

    def __init__(self, hierarchy='hierarchy.csv'):
        self.dependencies = []
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
    def __init__(self, reader, hierarchy='hierarchy.csv'):
        super(ReaderWeatherBundle, self).__init__(hierarchy)
        self.reader = reader

        self.load_readermeta(reader)
        self.load_regions()

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

    def baseline_average(self, maxyear):
        """Yield the average weather value up to `maxyear` for each region."""

        regionsums = np.zeros(len(self.regions))
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
        regioncols = np.array([[]] * len(self.regions)).transpose()

        # Append each year
        for yyyyddd, weather in self.yearbundles(maxyear):
            print int(yyyyddd[0]) / 1000

            # Stack this year below the previous years
            regioncols = np.vstack((regioncols, np.matrix(np.mean(weather, axis=0))))

        # Yield the entire collection of values for each region
        for ii in range(len(self.regions)):
            yield self.regions[ii], regioncols[:,ii].tolist()

    def baseline_bin_values(self, binlimits, maxyear):
        """Yield the number of days within each set of sequential limits from `binlimits` for each year and each region."""

        regioncolbins = []
        for ii in range(len(binlimits) - 1):
            regioncols = np.array([[]] * len(self.regions)).transpose()
            regioncolbins.append(regioncols)

        for yyyyddd, weather in self.yearbundles(maxyear):
            print int(yyyyddd[0]) / 1000

            for ii in range(len(binlimits) - 1):
                withinbin = np.logical_and(weather >= binlimits[ii], weather < binlimits[ii + 1])
                regioncolbins[ii] = np.vstack((regioncolbins[ii], np.matrix(np.sum(withinbin, axis=0))))

        for rr in range(len(self.regions)):
            yield self.regions[rr], [regioncolbins[ii][:,rr].ravel().tolist()[0] for ii in range(len(binlimits) - 1)]

class SingleWeatherBundle(DailyWeatherBundle, ReaderWeatherBundle):
    def is_historical(self):
        return False

    def yearbundles(self, maxyear=np.inf):
        for values in self.reader.read_iterator_to(maxyear):
            yield values

    def get_years(self):
        return self.reader.get_years()

class UnivariatePastFutureWeatherBundle(DailyWeatherBundle):
    def __init__(self, pastreader, futurereader, hierarchy='hierarchy.csv'):
        super(UnivariatePastFutureWeatherBundle, self).__init__(hierarchy)
        self.pastreader = pastreader
        self.futurereader = futurereader

        self.futureyear1 = min(self.futurereader.get_years())

        self.load_readermeta(futurereader)
        self.load_regions()

    def is_historical(self):
        return False

    def yearbundles(self, maxyear=np.inf):
        for values in self.pastreader.read_iterator_to(min(self.futureyear1, maxyear)):
            yield values

        for values in self.pastreader.read_iterator_to(maxyear):
            yield values

    def get_years(self):
        return np.unique(self.pastreader.get_years() + self.futurereader.get_years())

class RepeatedHistoricalWeatherBundle(DailyWeatherBundle):
    def __init__(self, reader, futureyear_end, seed, hierarchy='hierarchy.csv'):
        super(RepeatedHistoricalWeatherBundle, self).__init__(hierarchy)

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
            choices = range(self.pastyear_start, self.pastyear_end + 1)
            self.pastyears = np.random.choice(choices, self.futureyear_end - self.pastyear_start + 1)

        self.load_readermeta(reader)
        self.load_regions()

    def is_historical(self):
        return True

    @staticmethod
    def make_historical(weatherbundle, seed):
        futureyear_end = weatherbundle.get_years()[-1]
        return RepeatedHistoricalWeatherBundle(weatherbundle.pastreader, futureyear_end, seed)

    def yearbundles(self, maxyear=np.inf):
        year = self.pastyear_start
        for pastyear in self.pastyears:
            yyyyddd, weather = self.reader.read_year(pastyear)
            yield (1000 * year) + (yyyyddd % 1000), weather
            year += 1

    def get_years(self):
        return range(self.pastyear_start, self.futureyear_end + 1)

class MultivariateHistoricalWeatherBundle(DailyWeatherBundle):
    def __init__(self, template, year_start, year_end, variables,
                 hierarchy='hierarchy.csv', readncdf=netcdfs.readncdf):
        super(MultivariateHistoricalWeatherBundle, self).__init__(hierarchy)

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
        return range(self.year_start, self.year_end + 1)

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
    weatherbundle = MultivariateHistoricalWeatherBundle(template, 1981, 2005, ['pr', 'tas'])
    yyyyddd, weathers = weatherbundle.yearbundles().next()
    print len(yyyyddd), len(weathers), len(weathers[0]) # 365, 2, 365

    for region, weathers in weatherbundle.baseline_average(2005):
        print region, weathers
        exit()
