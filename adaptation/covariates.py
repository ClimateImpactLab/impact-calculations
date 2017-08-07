import numpy as np
import timeit
from econmodel import *
from datastore import agecohorts
from climate.yearlyreader import RandomYearlyAccess
from impactcommon.math import averages

## Class constructor with arguments (initial values, running length)
standard_running_mean_init = averages.BartlettAverager

class Covariator(object):
    """
    Provides both baseline data and updated covariates in response to each year's values.
    """
    def __init__(self, maxbaseline):
        self.startupdateyear = maxbaseline

    def get_current(self, region):
        raise NotImplementedError

    def get_update(self, region, year, ds):
        raise NotImplementedError

    def get_current_args(self, region):
        return (self.get_current(region),)

class EconomicCovariator(Covariator):
    def __init__(self, economicmodel, numeconyears, maxbaseline):
        super(EconomicCovariator, self).__init__(maxbaseline)

        self.numeconyears = numeconyears

        self.econ_predictors = economicmodel.baseline_prepared(maxbaseline, numeconyears, lambda values: standard_running_mean_init(values, numeconyears))
        self.economicmodel = economicmodel

    def get_econ_predictors(self, region):
        econpreds = self.econ_predictors.get(region, None)

        if econpreds is None:
            gdppc = self.econ_predictors['mean']['gdppc']
        else:
            gdppc = econpreds['gdppc'].get()

        if econpreds is None:
            density = self.econ_predictors['mean']['popop']
        else:
            density = econpreds['popop'].get()

        return dict(gdppc=gdppc, popop=density)

    def get_current(self, region):
        econpreds = self.get_econ_predictors(region)
        return dict(loggdppc=np.log(econpreds['gdppc']),
                    logpopop=np.log(econpreds['popop']))

    def get_update(self, region, year, ds):
        assert year < 10000

        if region in self.econ_predictors:
            gdppc = self.economicmodel.get_gdppc_year(region, year)
            if gdppc is not None and year > self.startupdateyear:
                self.econ_predictors[region]['gdppc'].update(gdppc)

            popop = self.economicmodel.get_popop_year(region, year)
            if popop is not None and year > self.startupdateyear:
                self.econ_predictors[region]['popop'].update(popop)

        gdppc = self.get_econ_predictors(region)['gdppc']
        popop = self.get_econ_predictors(region)['popop']

        return dict(loggdppc=np.log(gdppc), logpopop=np.log(popop), year=year)

class MeanWeatherCovariator(Covariator):
    def __init__(self, weatherbundle, numtempyears, maxbaseline, variable):
        super(MeanWeatherCovariator, self).__init__(maxbaseline)

        self.numtempyears = numtempyears
        self.variable = variable

        print "Collecting baseline information..."
        temp_predictors = {}
        for region, ds in weatherbundle.baseline_values(maxbaseline): # baseline through maxbaseline
            temp_predictors[region] = standard_running_mean_init(ds[variable][-numtempyears:], numtempyears)

        self.temp_predictors = temp_predictors
        self.weatherbundle = weatherbundle
        self.lastyear = {}

    def get_current(self, region):
        #assert region in self.temp_predictors, "Missing " + region
        return {self.variable: self.temp_predictors[region].get()}

    def get_update(self, region, year, ds):
        """Allow ds = None for dumb farmer who cannot adapt to temperature."""
        assert year < 10000
        # Ensure that we aren't called with a year twice
        assert self.lastyear.get(region, -np.inf) < year, "Called with %d, but previously did %d" % (year, self.lastyear.get(region, -np.inf))
        self.lastyear[region] = year

        if ds is not None and year > self.startupdateyear:
            self.temp_predictors[region].update(np.mean(ds[self.variable])) # if only yearly values

        return {self.variable: self.temp_predictors[region].get()}

class SeasonalWeatherCovariator(MeanWeatherCovariator):
    def __init__(self, weatherbundle, numtempyears, maxbaseline, day_start, day_end, variable):
        super(SeasonalWeatherCovariator, self).__init__(weatherbundle, numtempyears, maxbaseline)
        self.maxbaseline = maxbaseline
        self.day_start = day_start
        self.day_end = day_end
        self.variable = variable
        self.all_values = None

        self.mustr = "%smu%d-%d" % (self.weatherbundle.get_dimension()[0], self.day_start, self.day_end)
        self.sigmastr = "%ssigma%d-%d" % (self.weatherbundle.get_dimension()[0], self.day_start, self.day_end)

    def get_current(self, region):
        if self.all_values is None:
            print "Collecting " + self.mustr
            # Read in all regions
            self.all_values = {}
            for ds in self.weatherbundle.yearbundles(maxyear=self.maxbaseline):
                print ds.time[0]
                for region in self.weatherbundle.regions:
                    if region not in self.all_values:
                        self.all_values[region] = ds[self.variable].sel(region=region).values[self.day_start:self.day_end]
                    else:
                        self.all_values[region] = np.concatenate((self.all_values[region], ds[self.variable].sel(region=region).values[self.day_start:self.day_end]))

        mu = np.mean(self.all_values[region])
        sigma = np.std(self.all_values[region])

        return {self.mustr: mu, self.sigmastr: sigma}

    def get_update(self, region, year, ds):
        if ds is not None and year > self.startupdateyear:
            self.all_values[region] = np.concatenate((self.all_values[region][(self.day_end - self.day_start):], ds[self.variable][self.day_start:self.day_end]))

        mu = np.mean(self.all_values[region])
        sigma = np.std(self.all_values[region])

        return {self.mustr: mu, self.sigmastr: sigma}

class YearlyWeatherCovariator(Covariator):
    """
    YearlyWeatherCovariator takes a YearlyWeatherReader and collects
    data from it as needed, rather than depending on the
    weatherbundle.
    """
    def __init__(self, yearlyreader, regions, baseline_end, duration, is_historical):
        super(YearlyWeatherCovariator, self).__init__(baseline_end)

        predictors = {region: standard_running_mean_init([], duration) for region in regions}

        for years, values in yearlyreader.read_iterator():
            assert len(values) == 1
            for ii in range(len(regions)):
                predictors[regions[ii]].update(values[0, ii])

        self.predictors = predictors

        self.yearlyreader = yearlyreader
        self.regions = regions
        self.duration = duration
        self.is_historical = is_historical

        self.random_year_access = RandomYearlyAccess(yearlyreader)

    def get_current(self, region):
        return {self.yearlyreader.get_dimension()[0]: self.predictors[region].get()}

    def get_update(self, region, year, ds):
        if self.is_historical or ds is None:
            return self.get_current(region)

        assert year < 10000

        values = self.random_year_access.get_year(year).sel(region=region)
        self.predictors[region].update(values)

        return {self.yearlyreader.get_dimension()[0]: self.predictors[region].get()}

class MeanBinsCovariator(Covariator):
    def __init__(self, weatherbundle, binlimits, dropbin, numtempyears, maxbaseline):
        super(MeanBinsCovariator, self).__init__(maxbaseline)

        self.binlimits = binlimits
        self.dropbin = dropbin
        self.numtempyears = numtempyears

        print "Collecting baseline information..."
        temp_predictors = {} # {region: [rm-bin-1, ...]}
        for region, binyears in weatherbundle.baseline_values(maxbaseline): # baseline through maxbaseline
            usedbinyears = []
            for kk in range(binyears.shape[-1]):
                usedbinyears.append(standard_running_mean_init(binyears[-numtempyears:, kk], numtempyears))
            temp_predictors[region] = usedbinyears

        self.temp_predictors = temp_predictors
        self.weatherbundle = weatherbundle

    def get_current(self, region):
        #assert region in self.temp_predictors, "Missing " + region
        assert len(self.weatherbundle.get_dimension()) == len(self.temp_predictors[region])
        return {self.weatherbundle.get_dimension()[ii]: self.temp_predictors[region][ii].get() for ii in range(len(self.weatherbundle.get_dimension()))}

    def get_update(self, region, year, ds):
        assert year < 10000

        """Allow ds = None for dumb farmer who cannot adapt to temperature."""
        if temps is not None and year > self.startupdateyear:
            if len(temps.shape) == 1 and len(temps) == len(self.binlimits) - 1:
                for kk in range(len(self.binlimits) - 1):
                    self.temp_predictors[region][kk].update(np.sum(temps[kk]))
            elif len(temps.shape) == 2:
                if temps.shape[0] == 12 and temps.shape[1] == len(self.binlimits) - 1:
                    for kk in range(len(self.binlimits) - 1):
                        self.temp_predictors[region][kk].update(np.sum(temps[:, kk]))
                else:
                    raise RuntimeError("Unknown format for temps")
            else:
                belowprev = 0
                for kk in range(len(self.binlimits) - 2):
                    belowupper = float(np.sum(temps < self.binlimits[kk+1]))

                    self.temp_predictors[region][kk].update(belowupper - belowprev)
                    belowprev = belowupper
                self.temp_predictors[region][-1].update(len(temps) - belowprev)

        return {self.weatherbundle.get_dimension()[ii]: self.temp_predictors[region][ii].get() for ii in range(len(self.weatherbundle.get_dimension()))}

class AgeShareCovariator(Covariator):
    def __init__(self, economicmodel, numeconyears, maxbaseline):
        super(AgeShareCovariator, self).__init__(maxbaseline)

        self.numeconyears = numeconyears

        self.ageshares = agecohorts.load_ageshares(economicmodel.model, economicmodel.scenario)
        self.economicmodel = economicmodel

        self.agerm = {}
        self.get_current('mean') # Fill in the mean agerm

    def get_current(self, region):
        # Fill in the rm for this region
        if region != 'mean':
            region = region[:3] # Just country code
        if region not in self.ageshares:
            return {column: self.agerm['mean'][column].get() for column in agecohorts.columns}

        rmdata = {column: [] for column in agecohorts.columns} # {agecolumn: [values]}

        for year in range(min(self.ageshares[region].keys()), self.startupdateyear+1):
            if year in self.ageshares[region]:
                for cc in range(len(agecohorts.columns)):
                    rmdata[agecohorts.columns[cc]].append(self.ageshares[region][year][cc])

        for column in rmdata:
            rmdata[column] = standard_running_mean_init(rmdata[column][-self.numeconyears:], self.numeconyears)

        self.agerm[region] = rmdata

        return {column: rmdata[column].get() for column in agecohorts.columns}

    def get_update(self, region, year, ds):
        region = region[:3] # Just country code
        if region not in self.ageshares:
            region = 'mean' # XXX: This updates for every country!

        if region in self.agerm:
            if year in self.ageshares[region]:
                for cc in range(len(agecohorts.columns)):
                    self.agerm[region][agecohorts.columns[cc]].update(self.ageshares[region][year][cc])

        return {column: self.agerm[region][column].get() for column in agecohorts.columns}

class CombinedCovariator(Covariator):
    def __init__(self, covariators):
        for covariator in covariators[1:]:
            assert covariator.startupdateyear == covariators[0].startupdateyear

        super(CombinedCovariator, self).__init__(covariators[0].startupdateyear)
        self.covariators = covariators

    def get_current(self, region):
        result = {}
        for covariator in self.covariators:
            subres = covariator.get_current(region)
            for key in subres:
                result[key] = subres[key]

        return result

    def get_update(self, region, year, ds):
        result = {}
        for covariator in self.covariators:
            subres = covariator.get_update(region, year, ds)
            for key in subres:
                result[key] = subres[key]

        return result

class TranslateCovariator(Covariator):
    def __init__(self, covariator, renames, transforms={}):
        super(TranslateCovariator, self).__init__(covariator.startupdateyear)
        self.covariator = covariator
        self.renames = renames
        self.transforms = transforms

    def translate(self, covariates):
        result = {}
        for newname in self.renames:
            oldname = self.renames[newname]
            result[newname] = self.transforms.get(newname, lambda x: x)(covariates[oldname])

        return result

    def get_current(self, region):
        baseline = self.covariator.get_current(region)
        return self.translate(baseline)

    def get_update(self, region, year, ds):
        update = self.covariator.get_update(region, year, ds)
        return self.translate(update)
