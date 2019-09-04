import itertools
import numpy as np
from openest.generate import fast_dataset
from econmodel import *
from datastore import agecohorts, irvalues
from climate.yearlyreader import RandomYearlyAccess
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
        self.lastyear = {}

    def get_current(self, region):
        raise NotImplementedError

    def offer_update(self, region, year, ds):
        assert year < 10000
        # Ensure that we aren't called with a year twice
        assert self.lastyear.get(region, -np.inf) <= year, "Called with %d, but previously did %d" % (year, self.lastyear.get(region, -np.inf))
        if self.lastyear.get(region, -np.inf) < year:
            self.lastyear[region] = year
            return self.get_update(region, year, ds)

        return self.get_current(region)

    def get_update(self, region, year, ds):
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
                loggdppc = (loggdppc + self.baseline_loggdppc[region]) / 2
            else:
                loggdppc = (loggdppc + self.baseline_loggdppc['mean']) / 2
                
        return dict(loggdppc=loggdppc, popop=density)

    def get_current(self, region):
        econpreds = self.get_econ_predictors(region)
        return dict(loggdppc=econpreds['loggdppc'],
                    logpopop=np.log(econpreds['popop']),
                    year=self.lastyear.get(region, self.startupdateyear))

    def get_update(self, region, year, ds):
        assert year < 10000
        self.lastyear[region] = year

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

class BinnedEconomicCovariator(EconomicCovariator):
    def __init__(self, economicmodel, maxbaseline, limits, config={}):
        super(BinnedEconomicCovariator, self).__init__(economicmodel, maxbaseline, config=config)
        self.limits = limits

    def add_bins(self, covars):
        bin_limits = np.array(self.limits, dtype='float')
        incbin = np.digitize(covars['loggdppc'], bin_limits) # starts at 1
        for ii in range(1, len(self.limits)):
            covars['incbin' + str(ii)] = (incbin == ii)
        return covars
        
    def get_current(self, region):
        covars = super(BinnedEconomicCovariator, self).get_current(region)
        return self.add_bins(covars)

    def get_update(self, region, year, ds):
        covars = super(BinnedEconomicCovariator, self).get_update(region, year, ds)
        return self.add_bins(covars)

class ShiftedEconomicCovariator(EconomicCovariator):
    def __init__(self, economicmodel, maxbaseline, config={}):
        super(ShiftedEconomicCovariator, self).__init__(economicmodel, maxbaseline, config=config)
        assert 'loggdppc-delta' in config, "Must define loggdppc-delta to use loggdppc-shifted."
        self.delta = config['loggdppc-delta']

    def add_shifted(self, covars):
        covars['loggdppc-shifted'] = covars['loggdppc'] - self.delta
        return covars
        
    def get_current(self, region):
        covars = super(ShiftedEconomicCovariator, self).get_current(region)
        return self.add_shifted(covars)

    def get_update(self, region, year, ds):
        covars = super(ShiftedEconomicCovariator, self).get_update(region, year, ds)
        return self.add_shifted(covars)

class MeanWeatherCovariator(Covariator):
    def __init__(self, weatherbundle, maxbaseline, variable, config={}, quiet=False):
        super(MeanWeatherCovariator, self).__init__(maxbaseline)

        self.numtempyears = config.get('length', standard_climate_config['length'])
        self.variable = variable

        if not quiet:
            print "Collecting baseline information..."
        temp_predictors = {}
        for region, ds in weatherbundle.baseline_values(maxbaseline, quiet=quiet): # baseline through maxbaseline
            try:
                temp_predictors[region] = averages.interpret(config, standard_climate_config, ds[variable][-self.numtempyears:])
            except Exception as ex:
                print "Cannot retrieve baseline data for %s" % variable
                print ds
                raise ex

        self.temp_predictors = temp_predictors
        self.weatherbundle = weatherbundle

    def get_current(self, region):
        #assert region in self.temp_predictors, "Missing " + region
        return {self.variable: self.temp_predictors[region].get()}

    def get_update(self, region, year, ds):
        """Allow ds = None for incadapt farmer who cannot adapt to temperature."""
        if ds is not None and year > self.startupdateyear:
            self.temp_predictors[region].update(np.mean(ds[self.variable]._values)) # if only yearly values

        return {self.variable: self.temp_predictors[region].get(), 'year': year}

class SubspanWeatherCovariator(MeanWeatherCovariator):
    def __init__(self, weatherbundle, maxbaseline, day_start, day_end, variable, config={}):
        super(SubspanWeatherCovariator, self).__init__(weatherbundle, maxbaseline, variable, config=config)
        self.maxbaseline = maxbaseline
        self.day_start = day_start
        self.day_end = day_end
        self.all_values = None

        self.mustr = "%smu%d-%d" % (variable, self.day_start, self.day_end)
        self.sigmastr = "%ssigma%d-%d" % (variable, self.day_start, self.day_end)

    def get_current(self, region):
        if self.all_values is None:
            print "Collecting " + self.mustr
            # Read in all regions
            self.all_values = {}
            for year, ds in self.weatherbundle.yearbundles(maxyear=self.maxbaseline):
                print year
                for region in self.weatherbundle.regions:
                    if region not in self.all_values:
                        self.all_values[region] = np.squeeze(ds[self.variable].sel(region=region).values[self.day_start:self.day_end])
                    else:
                        self.all_values[region] = np.concatenate((self.all_values[region], np.squeeze(ds[self.variable].sel(region=region).values[self.day_start:self.day_end])))

        mu = np.mean(self.all_values[region])
        sigma = np.std(self.all_values[region])

        return {self.mustr: mu, self.sigmastr: sigma}

    def get_update(self, region, year, ds):
        if self.all_values is None:
            self.get_current(region)
            
        if ds is not None and year > self.startupdateyear:
            self.all_values[region] = np.concatenate((self.all_values[region][(self.day_end - self.day_start):], np.squeeze(ds[self.variable][self.day_start:self.day_end])))

        mu = np.mean(self.all_values[region])
        sigma = np.std(self.all_values[region])

        return {self.mustr: mu, self.sigmastr: sigma}

class SeasonalWeatherCovariator(MeanWeatherCovariator):
    def __init__(self, weatherbundle, maxbaseline, filepath, variable, config={}):
        super(SeasonalWeatherCovariator, self).__init__(weatherbundle, maxbaseline, variable, config=config)
        self.maxbaseline = maxbaseline
        assert config['timerate'] == 'month', "Cannot handle daily seasons."
        self.culture_periods = irvalues.get_file_cached(filepath, irvalues.load_culture_months)

        # Setup all averages
        self.byregion = {region: averages.interpret(config, standard_climate_config, []) for region in self.weatherbundle.regions}

        for year, ds in self.weatherbundle.yearbundles(maxyear=self.maxbaseline):
            regions = np.array(ds.region)
            for region, subds in fast_dataset.region_groupby(ds, year, regions, {regions[ii]: ii for ii in range(len(regions))}):
                if region in self.culture_periods:
                    plantii = int(self.culture_periods[region][0] - 1)
                    harvestii = int(self.culture_periods[region][1] - 1)
                    self.byregion[region].update(np.mean(subds[self.variable]._values[plantii:harvestii]))

    def get_current(self, region):
        if region in self.culture_periods:
            return {'seasonal' + self.variable: self.byregion[region].get()}
        else:
            return {'seasonal' + self.variable: np.nan}

    def get_update(self, region, year, ds):
        if ds is not None and year > self.startupdateyear:
            if region in self.culture_periods:
                plantii = int(self.culture_periods[region][0] - 1)
                harvestii = int(self.culture_periods[region][1] - 1)
                self.byregion[region].update(np.mean(ds[self.variable]._values[plantii:harvestii]))

        return self.get_current(region)

def get_single_value(numpylike):
    dims = np.sum(np.array(numpylike).shape)
    if dims == 0:
        return numpylike
    elif dims == 1:
        return numpylike[0]
    else:
        assert dims <= 1, "Must be a single value."
    
class YearlyWeatherCovariator(Covariator):
    """
    YearlyWeatherCovariator takes a YearlyWeatherReader and collects
    data from it as needed, rather than depending on the
    weatherbundle.
    """
    def __init__(self, yearlyreader, regions, baseline_end, is_historical, config={}):
        super(YearlyWeatherCovariator, self).__init__(baseline_end)

        predictors = {region: averages.interpret(config, standard_climate_config, []) for region in regions}

        for ds in yearlyreader.read_iterator():
            year = get_single_value(ds[yearlyreader.timevar])
            for ii in range(len(regions)):
                predictors[regions[ii]].update(ds[yearlyreader.variables[0]][ii])
            if year == baseline_end:
                break

        self.predictors = predictors

        self.yearlyreader = yearlyreader
        self.regions = regions
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
    def __init__(self, weatherbundle, binlimits, dropbin, maxbaseline, config={}, quiet=False):
        super(MeanBinsCovariator, self).__init__(maxbaseline)

        self.binlimits = binlimits
        self.dropbin = dropbin
        self.numtempyears = config.get('length', standard_climate_config['length'])

        if not quiet:
            print "Collecting baseline information..."
        temp_predictors = {} # {region: [rm-bin-1, ...]}
        for region, binyears in weatherbundle.baseline_values(maxbaseline, quiet=quiet): # baseline through maxbaseline
            usedbinyears = []
            for kk in range(binyears.shape[-1]):
                usedbinyears.append(averages.interpret(config, standard_climate_config, binyears[-self.numtempyears:, kk]))
            temp_predictors[region] = usedbinyears

        self.temp_predictors = temp_predictors
        self.weatherbundle = weatherbundle

    def get_current(self, region):
        #assert region in self.temp_predictors, "Missing " + region
        assert len(self.weatherbundle.get_dimension()) == len(self.temp_predictors[region])
        return {self.weatherbundle.get_dimension()[ii]: self.temp_predictors[region][ii].get() for ii in range(len(self.weatherbundle.get_dimension()))}

    def get_update(self, region, year, ds):
        assert year < 10000

        """Allow ds = None for incadapt farmer who cannot adapt to temperature."""
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

    def get_update(self, region, year, ds):
        region = region[:3] # Just country code
        if region not in self.ageshares:
            region = 'mean' # XXX: This updates for every country!

        if region in self.agerm:
            if year in self.ageshares[region]:
                for cc in range(len(agecohorts.columns)):
                    self.agerm[region][agecohorts.columns[cc]].update(self.ageshares[region][year][cc])

        return {column: self.agerm[region][column].get() for column in agecohorts.columns}

class ConstantCovariator(Covariator):
    def __init__(self, name, irvalues):
        super(ConstantCovariator, self).__init__(None)
        self.name = name
        self.irvalues = irvalues

    def get_current(self, region):
        return {self.name: self.irvalues[region]}

    def get_update(self, region, year, ds):
        return {self.name: self.irvalues[region]}
    
class CombinedCovariator(Covariator):
    def __init__(self, covariators):
        commonstartyear = None
        for covariator in covariators:
            if covariator.startupdateyear is not None:
                if commonstartyear is not None:
                    assert covariator.startupdateyear == commonstartyear
                else:
                    commonstartyear = covariator.startupdateyear

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

class HistoricalCovariator(Covariator):
    """Just don't ignore get_update; note that this means that the source
covariator should not be used elsewhere where it might have get_update
called.
    """
    def __init__(self, source, suffix):
        super(HistoricalCovariator, self).__init__(source.startupdateyear)
        self.source = source
        self.suffix = suffix

    def get_update(self, region, year, ds):
        return self.get_current(region)

    def get_current(self, region):
        covariates = self.source.get_current(region)
        return {covar + self.suffix: covariates[covar] for covar in covariates}

class ProductCovariator(Covariator):
    def __init__(self, source1, source2):
        assert source1.startupdateyear == source2.startupdateyear
        super(ProductCovariator, self).__init__(source1.startupdateyear)
        self.source1 = source1
        self.source2 = source2

    def make_product(self, covars1, covars2):
        combos = itertools.product(covars1.keys(), covars2.keys())
        result = {"%s*%s" % (key1, key2): covars1[key1] * covars2[key2] for key1, key2 in combos}
        if 'year' in covars1:
            result['year'] = covars1['year']
        if 'year' in covars2:
            result['year'] = covars2['year']
        return result
        
    def get_update(self, region, year, ds):
        covars1 = self.source1.get_update(region, year, ds)
        covars2 = self.source2.get_update(region, year, ds)
        return self.make_product(covars1, covars2)

    def get_current(self, region):
        covars1 = self.source1.get_current(region)
        covars2 = self.source2.get_current(region)
        return self.make_product(covars1, covars2)
    
class PowerCovariator(Covariator):
    def __init__(self, source, power):
        super(PowerCovariator, self).__init__(source.startupdateyear)
        self.source = source
        self.power = power

    def make_power(self, covars):
        return {"%s^%g" % (key, self.power): covars[key] ** self.power for key in covars}
        
    def get_update(self, region, year, ds):
        covars = self.source.get_update(region, year, ds)
        return self.make_power(covars)

    def get_current(self, region):
        covars = self.source.get_current(region)
        return self.make_power(covars)
