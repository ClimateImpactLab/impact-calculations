import numpy as np
from econmodel import *
from datastore import agecohorts
from climate.yearlyreader import RandomYearlyAccess, RandomRegionAccess
from interpret import averages

## Class constructor with arguments (initial values, running length)
standard_economic_config = {'class': 'bartlett', 'length': 13}
standard_climate_config = {'class': 'bartlett', 'length': 30}

class Covariator(object):
    """
    Provides both baseline data and updated covariates in response to each year's values.
    """
    def __init__(self, maxbaseline):
        self.startupdateyear = maxbaseline

    def get_current(self, region):
        raise NotImplementedError

    def get_update(self, region, year, weather):
        raise NotImplementedError

    def get_current_args(self, region):
        return (self.get_current(region),)

class EconomicCovariator(Covariator):
    def __init__(self, economicmodel, maxbaseline, config={}):
        super(EconomicCovariator, self).__init__(maxbaseline)

        self.numeconyears = config.get('length', standard_economic_config['length'])

        self.econ_predictors = economicmodel.baseline_prepared(maxbaseline, self.numeconyears, lambda values: averages.interpret(config, standard_economic_config, values))
        self.economicmodel = economicmodel

        if config.get('slowadapt', 'none') in ['income', 'both']:
            self.slowgrowth = True
            self.baseline_loggdppc = {region: self.econ_predictors[region]['loggdppc'].get() for region in self.econ_predictors}
            self.baseline_loggdppc['mean'] = np.mean(self.baseline_loggdppc.values())
        else:
            self.slowgrowth = False

    def get_econ_predictors(self, region):
        econpreds = self.econ_predictors.get(region, None)

        if econpreds is None:
            print "ERROR: Missing econpreds for %s." % region
            loggdppc = self.econ_predictors['mean']['loggdppc']
        else:
            loggdppc = econpreds['loggdppc'].get()

        if econpreds is None:
            density = self.econ_predictors['mean']['popop']
        else:
            density = econpreds['popop'].get()

        if self.slowgrowth:
            # Equivalent to baseline * exp(growth * time / 2)
            if region in self.baseline_loggdppc:
                loggdppc = (loggdppc + self.baseline_loggdppc[region]) * 2
            else:
                loggdppc = (loggdppc + self.baseline_loggdppc['mean']) * 2
                
        return dict(loggdppc=loggdppc, popop=density)

    def get_current(self, region):
        econpreds = self.get_econ_predictors(region)
        return dict(loggdppc=econpreds['loggdppc'],
                    logpopop=np.log(econpreds['popop']))

    def get_update(self, region, year, temps):
        assert year < 10000

        if region in self.econ_predictors:
            loggdppc = self.economicmodel.get_loggdppc_year(region, year)
            if loggdppc is not None and year > self.startupdateyear:
                self.econ_predictors[region]['loggdppc'].update(loggdppc)

            popop = self.economicmodel.get_popop_year(region, year)
            if popop is not None and year > self.startupdateyear:
                self.econ_predictors[region]['popop'].update(popop)

        loggdppc = self.get_econ_predictors(region)['loggdppc']
        popop = self.get_econ_predictors(region)['popop']

        return dict(loggdppc=loggdppc, logpopop=np.log(popop), year=year)

class MeanWeatherCovariator(Covariator):
    def __init__(self, weatherbundle, maxbaseline, config={}, varindex=None):
        super(MeanWeatherCovariator, self).__init__(maxbaseline)

        self.numtempyears = config.get('length', standard_climate_config['length'])
        self.varindex = varindex

        print "Collecting baseline information..."
        temp_predictors = {}
        for region, temps in weatherbundle.baseline_values(maxbaseline): # baseline through maxbaseline
            if varindex is None:
                assert len(temps.shape) == 1
                temp_predictors[region] = averages.interpret(config, standard_climate_config, temps[-self.numtempyears:])
            else:
                temp_predictors[region] = averages.interpret(config, standard_climate_config, temps[-self.numtempyears:, varindex])

        self.temp_predictors = temp_predictors
        self.weatherbundle = weatherbundle
        self.lastyear = {}

        if config.get('slowadapt', 'none') in ['both', 'temperature']:
            self.slowadapt = True
            baseline_predictors = {}
            for region in temp_predictors:
                baseline_predictors[region] = temp_predictors[region].get()
            self.baseline_predictors = baseline_predictors
        else:
            self.slowadapt = False

    def get_current(self, region):
        #assert region in self.temp_predictors, "Missing " + region
        if self.slowadapt:
            if self.varindex is None:
                return {self.weatherbundle.get_dimension()[0]: (self.temp_predictors[region].get() + self.baseline_predictors[region]) * 2}
            else:
                return {self.weatherbundle.get_dimension()[self.varindex]: (self.temp_predictors[region].get() + self.baseline_predictors[region]) * 2}
        else:
            if self.varindex is None:
                return {self.weatherbundle.get_dimension()[0]: self.temp_predictors[region].get()}
            else:
                return {self.weatherbundle.get_dimension()[self.varindex]: self.temp_predictors[region].get()}

    def get_update(self, region, year, temps):
        """Allow temps = None for dumb farmer who cannot adapt to temperature."""
        assert year < 10000
        # Ensure that we aren't called with a year twice
        assert self.lastyear.get(region, -np.inf) < year, "Called with %d, but previously did %d" % (year, self.lastyear.get(region, -np.inf))
        self.lastyear[region] = year

        if temps is not None and year > self.startupdateyear:
            if self.varindex is None:
                self.temp_predictors[region].update(np.mean(temps))
            elif len(temps.shape) == 1:
                self.temp_predictors[region].update(np.mean(temps[self.varindex])) # if only yearly values
            else:
                self.temp_predictors[region].update(np.mean(temps[:, self.varindex]))

        if self.slowadapt:
            if self.varindex is None:
                return {self.weatherbundle.get_dimension()[0]: (self.temp_predictors[region].get() + self.baseline_predictors[region]) * 2}
            else:
                return {self.weatherbundle.get_dimension()[self.varindex]: (self.temp_predictors[region].get() + self.baseline_predictors[region]) * 2}
        else:
            if self.varindex is None:
                return {self.weatherbundle.get_dimension()[0]: self.temp_predictors[region].get()}
            else:
                return {self.weatherbundle.get_dimension()[self.varindex]: self.temp_predictors[region].get()}

class SeasonalWeatherCovariator(MeanWeatherCovariator):
    def __init__(self, weatherbundle, maxbaseline, day_start, day_end, config={}, varindex=None):
        super(SeasonalWeatherCovariator, self).__init__(weatherbundle, maxbaseline, config=config)
        self.maxbaseline = maxbaseline
        self.day_start = day_start
        self.day_end = day_end
        self.varindex = varindex
        self.all_values = None

        self.mustr = "%smu%d-%d" % (self.weatherbundle.get_dimension()[0], self.day_start, self.day_end)
        self.sigmastr = "%ssigma%d-%d" % (self.weatherbundle.get_dimension()[0], self.day_start, self.day_end)

    def get_current(self, region):
        if self.all_values is None:
            print "Collecting " + self.mustr
            # Read in all regions
            self.all_values = {}
            for weatherslice in self.weatherbundle.yearbundles(maxyear=self.maxbaseline):
                print weatherslice.times[0]
                for ii in range(len(self.weatherbundle.regions)):
                    if self.weatherbundle.regions[ii] not in self.all_values:
                        self.all_values[self.weatherbundle.regions[ii]] = weatherslice.weathers[self.day_start:self.day_end, ii]
                    else:
                        self.all_values[self.weatherbundle.regions[ii]] = np.concatenate((self.all_values[self.weatherbundle.regions[ii]], weatherslice.weathers[self.day_start:self.day_end, ii]))

        mu = np.mean(self.all_values[region])
        sigma = np.std(self.all_values[region])

        return {self.mustr: mu, self.sigmastr: sigma}

    def get_update(self, region, year, weather):
        if weather is not None and year > self.startupdateyear:
            self.all_values[region] = np.concatenate((self.all_values[region][(self.day_end - self.day_start):], weather[self.day_start:self.day_end, self.varindex]))

        mu = np.mean(self.all_values[region])
        sigma = np.std(self.all_values[region])

        return {self.mustr: mu, self.sigmastr: sigma}

class YearlyWeatherCovariator(Covariator):
    """
    YearlyWeatherCovariator takes a YearlyWeatherReader and collects
    data from it as needed, rather than depending on the
    weatherbundle.
    """
    def __init__(self, yearlyreader, regions, baseline_end, is_historical, config={}):
        super(YearlyWeatherCovariator, self).__init__(baseline_end)

        predictors = {region: averages.interpret(config, standard_climate_config, []) for region in regions}

        for weatherslice in yearlyreader.read_iterator():
            assert len(weatherslice.times) == 1
            for ii in range(len(regions)):
                predictors[regions[ii]].update(weatherslice.weathers[0, ii])
            if weatherslice.get_years()[0] == baseline_end:
                break

        self.predictors = predictors

        self.yearlyreader = yearlyreader
        self.regions = regions
        self.is_historical = is_historical

        random_year_access = RandomYearlyAccess(yearlyreader)
        self.random_region_access = RandomRegionAccess(random_year_access.get_year, regions)

    def get_current(self, region):
        return {self.yearlyreader.get_dimension()[0]: self.predictors[region].get()}

    def get_update(self, region, year, temps):
        if self.is_historical or temps is None:
            return self.get_current(region)

        assert year < 10000

        values = self.random_region_access.get_region_year(region, year)
        self.predictors[region].update(values)

        return {self.yearlyreader.get_dimension()[0]: self.predictors[region].get()}

class MeanBinsCovariator(Covariator):
    def __init__(self, weatherbundle, binlimits, dropbin, maxbaseline, config={}):
        super(MeanBinsCovariator, self).__init__(maxbaseline)

        self.binlimits = binlimits
        self.dropbin = dropbin
        self.numtempyears = config.get('length', standard_climate_config['length'])

        print "Collecting baseline information..."
        temp_predictors = {} # {region: [rm-bin-1, ...]}
        for region, binyears in weatherbundle.baseline_values(maxbaseline): # baseline through maxbaseline
            usedbinyears = []
            for kk in range(binyears.shape[-1]):
                usedbinyears.append(averages.interpret(config, standard_climate_config, binyears[-numtempyears:, kk]))
            temp_predictors[region] = usedbinyears

        self.temp_predictors = temp_predictors
        self.weatherbundle = weatherbundle

    def get_current(self, region):
        #assert region in self.temp_predictors, "Missing " + region
        assert len(self.weatherbundle.get_dimension()) == len(self.temp_predictors[region])
        return {self.weatherbundle.get_dimension()[ii]: self.temp_predictors[region][ii].get() for ii in range(len(self.weatherbundle.get_dimension()))}

    def get_update(self, region, year, temps):
        assert year < 10000

        """Allow temps = None for dumb farmer who cannot adapt to temperature."""
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
    def __init__(self, economicmodel, maxbaseline, config={}):
        super(AgeShareCovariator, self).__init__(maxbaseline)

        self.config = config

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
            rmdata[column] = averages.interpret(config, standard_economic_config, rmdata[column])

        self.agerm[region] = rmdata

        return {column: rmdata[column].get() for column in agecohorts.columns}

    def get_update(self, region, year, temps):
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

    def get_update(self, region, year, temps):
        result = {}
        for covariator in self.covariators:
            subres = covariator.get_update(region, year, temps)
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

    def get_update(self, region, year, temps):
        update = self.covariator.get_update(region, year, temps)
        return self.translate(update)

class CountryAggregatedCovariator(Covariator):
    def __init__(self, source, regions):
        self.source = source
        bycountry = {}
        for region in regions:
            if region[:3] in bycountry:
                bycountry[region[:3]].append(region)
            else:
                bycountry[region[:3]] = [region]
        self.bycountry = bycountry

    def get_current(self, country):
        values = [self.source.get_current(region) for region in self.bycountry[country]]
        return {key: np.mean([value[key] for value in values]) for key in values[0]}

class CountryDeviationCovariator(CountryAggregatedCovariator):
    def get_current(self, region):
        countrylevel = super(CountryDeviationCovariator, self).get_current(region[:3])
        subcountrylevel = self.source.get_current(region)

        return {key: subcountrylevel[key] - countrylevel[key] for key in subcountrylevel}
