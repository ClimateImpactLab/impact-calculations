import os, re, csv
import numpy as np
from netCDF4 import Dataset
from helpers import files
import helpers.header as headre

def get_arbitrary_variables(path):
    variables = {} # result of the function

    # Find all netcdfs within this directory
    for root, dirs, files in os.walk(path):
        for filename in files:
            # Check the filename
            match = re.match(r'.*?(pr|tasmin|tasmax|tas).*?\.nc', filename)
            if match:
                variable = match.group(1)
                filepath = os.path.join(root, filename)
                variables[variable] = filepath # add to the result set
                print "Found %s: %s" % (variable, filepath)

    return variables

def readmeta(filepath, variable):
    """
    Return version, units.
    """
    rootgrp = Dataset(filepath, 'r', format='NETCDF4')
    version = rootgrp.version
    units = rootgrp.variables[variable].units
    rootgrp.close()

    return version, units

def readncdf(filepath, variable):
    """
    Return yyyyddd, weather
    """
    rootgrp = Dataset(filepath, 'r', format='NETCDF4')
    weather = rootgrp.variables[variable][:,:]
    yyyyddd = rootgrp.variables['time'][:]
    rootgrp.close()

    return yyyyddd, weather

def iterate_bundles(basedir):
    """
    Return bundles for each RCP and model.

    basedir points to directory with both 'historical', 'rcp*'
    """
    # Collect the entire complement of models
    models = set()
    for filename in os.listdir(os.path.join(basedir, 'historical/tas')):
        result = re.match(r'tas_day_aggregated_historical_r1i1p1_(.+)_\d{4}\.nc', filename)
        if result:
            models.add(result.group(1))

    for scenario in os.listdir(basedir):
        if scenario[0:3] != 'rcp':
            continue

        for model in models:
            pasttemplate = os.path.join(basedir, 'historical/tas/tas_day_aggregated_historical_r1i1p1_' + model + '_%d.nc')
            futuretemplate = os.path.join(basedir, scenario, 'tas/tas_day_aggregated_' + scenario + '_r1i1p1_' + model + '_%d.nc')
            weatherbundle = UnivariatePastFutureWeatherBundle(pasttemplate, 1981, futuretemplate, 2006, 'tas')
            yield scenario, model, weatherbundle

class WeatherBundle(object):
    def __init__(self, hierarchy='hierarchy.csv'):
        self.dependencies = []
        self.hierarchy = hierarchy
        
    def load_regions(self):
        mapping = {} # color to hierid

        with open(files.datapath("regions/" + self.hierarchy), 'r') as fp:
            reader = csv.reader(headre.deparse(fp, self.dependencies))
            header = reader.next()
            for row in reader:
                if row[header.index('agglomid')]:
                    mapping[int(row[header.index('agglomid')])] = row[0]

        self.regions = []
        for ii in range(len(mapping)):
            self.regions.append(mapping[ii + 1])

    def load_metainfo(self, filepath, variable):
        self.version, self.units = readmeta(filepath, variable)

    def baseline_average(self, maxyear):
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
        regioncols = np.array([[]] * len(self.regions)).transpose()
        print regioncols.shape
        for yyyyddd, weather in self.yearbundles(maxyear):
            print int(yyyyddd[0]) / 1000

            regioncols = np.vstack((regioncols, np.matrix(np.mean(weather, axis=0))))

        for ii in range(len(self.regions)):
            yield self.regions[ii], regioncols[:,ii].tolist()

    def baseline_bin_values(self, binlimits, maxyear):
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

class UnivariatePastFutureWeatherBundle(WeatherBundle):
    def __init__(self, pasttemplate, pastyear1, futuretemplate, futureyear1,
                 variable, hierarchy='hierarchy.csv'):
        super(UnivariatePastFutureWeatherBundle, self).__init__(hierarchy)
        self.pasttemplate = pasttemplate
        self.pastyear1 = pastyear1
        self.futuretemplate = futuretemplate
        self.futureyear1 = futureyear1
        self.variable = variable

        self.load_regions()
        self.load_metainfo(self.pasttemplate % (pastyear1), variable)

    def is_historical(self):
        return False

    def yearbundles(self, maxyear=np.inf):
        for year in range(self.pastyear1, min(self.futureyear1, maxyear)):
            yield readncdf(self.pasttemplate % (year), self.variable)

        year = self.futureyear1
        while os.path.exists(self.futuretemplate % (year)) and year <= maxyear:
            yield readncdf(self.futuretemplate % (year), self.variable)
            year += 1

    def get_years(self):
        years = range(self.pastyear1, self.futureyear1)

        year = self.futureyear1
        while os.path.exists(self.futuretemplate % (year)):
            years.append(year)
            year += 1

        return years

class RepeatedHistoricalWeatherBundle(WeatherBundle):
    def __init__(self, pasttemplate, pastyear_start, pastyear_end, futureyear_end, variable,
                 seed, hierarchy='hierarchy.csv'):
        super(RepeatedHistoricalWeatherBundle, self).__init__(hierarchy)

        self.pasttemplate = pasttemplate
        self.pastyear_start = pastyear_start
        self.pastyear_end = pastyear_end
        self.futureyear_end = futureyear_end
        self.variable = variable

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

        self.load_regions()
        self.load_metainfo(self.pasttemplate % (self.pastyear_start), variable)

    def is_historical(self):
        return True

    @staticmethod
    def make_historical(weatherbundle, seed):
        futureyear_end = weatherbundle.get_years()[-1]
        return RepeatedHistoricalWeatherBundle(weatherbundle.pasttemplate, weatherbundle.pastyear1,
                                               weatherbundle.futureyear1 - 1, futureyear_end, weatherbundle.variable, seed)

    def yearbundles(self, maxyear=np.inf):
        year = self.pastyear_start
        for pastyear in self.pastyears:
            yyyyddd, weather = readncdf(self.pasttemplate % (pastyear), self.variable)
            yield (1000 * year) + (yyyyddd % 1000), weather
            year += 1

    def get_years(self):
        return range(self.pastyear_start, self.futureyear_end + 1)
