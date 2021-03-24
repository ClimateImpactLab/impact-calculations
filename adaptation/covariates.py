"""Defines the covariate construction system.

Covariates, like income and long-run temperature, are the basis for
describing adaptation in the GCP.

Covariates are provided by `Covariator` objects.  Each calculation has
a single Covariator, which may itself contain other Covariators to
produce a collection of covariates.

Initially, the covariate has a baseline value. This value is computed
up to a given year, the `maxbaseline` year. It is held constant at
this value up to that point.  Then it calculates an updated value each
year, providing this value to all who ask for it until the next year.

Covariates are averaged across multiple years, using a running average
object with a specific kernel and length. This system is defined in
`impactcommon.math.averages`.

The different subclasses of Covariator provide different kinds of
covariates. In general, climate covariates rely on the weather data
being pushed through the projection calculation. Socioeconomic
coviarates, however, have some other object as a source of the
information and the Covariator object just manages the baselining and
averaging.
"""

import itertools
from collections import defaultdict
import numpy as np
import xarray as xr
from pandas import read_csv
from openest.generate import fast_dataset
from impactlab_tools.utils import files
from .econmodel import *
from datastore import agecohorts, irvalues, irregions
from climate.yearlyreader import RandomYearlyAccess
from interpret import averages, configs


## Class constructor with arguments (initial values, running length)
standard_economic_config = {'class': 'bartlett', 'length': 13}
standard_climate_config = {'class': 'bartlett', 'length': 30}

class Covariator(object):
    """
    Provides both baseline data and updated covariates in response to each year's values.

    Parameters
    ----------
    maxbaseline : int
        Year up to which the covariate baseline is calculated.
    conf : dict or None, optional
        Configuration dict.
    """
    def __init__(self, maxbaseline, config=None):
        if config is None:
            config = {}
        self.startupdateyear = maxbaseline
        self.lastyear = {}
        self.yearcovarscale = config.get('yearcovarscale', 1)

    def get_yearcovar(self, region):
        """
        Parameters
        ----------
        region : str
            Target impact region.

        Returns
        -------
        year
        """
        year = self.lastyear.get(region, self.startupdateyear)
        if year > self.startupdateyear:
            return (year - self.startupdateyear) * self.yearcovarscale + self.startupdateyear
        else:
            return year
        
    def get_current(self, region):
        """
        This can be called as many times as we want.

        Parameters
        ----------
        region : str
        """
        raise NotImplementedError

    def offer_update(self, region, year, ds):
        """

        This can be called as many times as we want.

        Parameters
        ----------
        region : str
        year : int
        ds : xarray.Dataset
        """
        assert year < 10000
        # Ensure that we aren't called with a year twice
        assert self.lastyear.get(region, -np.inf) <= year, "Called with %d, but previously did %d" % (year, self.lastyear.get(region, -np.inf))
        if self.lastyear.get(region, -np.inf) < year:
            self.lastyear[region] = year
            return self.get_update(region, year, ds)

        return self.get_current(region)

    def get_update(self, region, year, ds):
        """
        This should only be called by `offer_update`, because it can only be called once per year-region combination.

        Parameters
        ----------
        region : str
        year : int
        ds : xarray.Dataset
        """
        raise NotImplementedError

    def get_current_args(self, region):
        """
        Parameters
        ----------
        region : str

        Returns
        -------
        tuple
        """
        return (self.get_current(region),)

class GlobalExogenousCovariator(Covariator):
    """Produces a externally given sequence of covariate values for all regions.

    {'covarname': `baseline`} will returned up to (and including) `startupdateyear`.
    In `startupdateyear` + N, the Nth value of `values` will be returned (`values[N-1]`).

    Parameters
    ----------
    startupdateyear : year
        Last year to report `baseline` value.
    covarname : str
        Covariate name to report.
    baseline : float or int
        The value to report up to `startupdateyear`.
    values : Sequence of floats
        Values to report after `startupdateyear`.
    """
    def __init__(self, startupdateyear, covarname, baseline, values):
        super(GlobalExogenousCovariator, self).__init__(startupdateyear)
        self.covarname = covarname
        self.values = values
        self.cached_value = baseline
        self.cached_index = -1

    def get_current(self, region):
        """
        Parameters
        ----------
        region : str
        """
        return {self.covarname: self.cached_value}

    def get_update(self, region, year, ds):
        """
        Parameters
        ----------
        region : str
        year : int
        ds : xarray.Dataset
        """
        if year > self.startupdateyear:
            self.cached_index += 1
            self.cached_value = self.values[self.cached_index]
        return self.get_current(region)

class EconomicCovariator(Covariator):
    """Provides information on log GDP per capita and Population-weight population density.

    Parameters
    ----------
    economicmodel : adaptation.SSPEconomicModel
    maxbaseline : int
        Year up to which the covariate baseline is calculated.
    limits : Sequence of float
    country_level : bool, optional
        Whether economic covariators are to be used at the country level.
        If ``True``, any ``region`` str passed into methods will be split on
        ".", and values for the first segment of the split name will be used.
    conf : dict or None, optional
        Configuration dict.
    """
    def __init__(self, economicmodel, maxbaseline, country_level=False, config=None):
        super(EconomicCovariator, self).__init__(maxbaseline, config=config)

        if config is None:
            config = {}
        self.numeconyears = config.get('length', standard_economic_config['length'])

        self.econ_predictors = economicmodel.baseline_prepared(maxbaseline, self.numeconyears, lambda values: averages.interpret(config, standard_economic_config, values))
        self.economicmodel = economicmodel

        config = configs.search_slowadapt(config)
        config_scale_covariate_changes = config.get('scale-covariate-changes', None)

        self.baseline_loggdppc = {region: self.econ_predictors[region]['loggdppc'].get() for region in self.econ_predictors}
        self.baseline_loggdppc['mean'] = np.mean(list(self.baseline_loggdppc.values()))

        if config_scale_covariate_changes is not None and 'income' in config_scale_covariate_changes:
            self.covariates_scalar = config_scale_covariate_changes['income']
        else:
            self.covariates_scalar = 1

        assert self.covariates_scalar > 0, 'scale-covariate-changes should be a strictly positive float'

        self.country_level = bool(country_level)

    @staticmethod
    def _get_root_region(x):
        """Break hierid str into components and return str of root region
        """
        return str(x.split(".")[0])

    def get_econ_predictors(self, region):
        """
        Parameters
        ----------
        region : str

        Returns
        -------
        dict
            Output has keys "loggdppc" and "popop" giving the nautral log per
            capita GDP and some other value.
        """
        region = self._get_root_region(region) if self.country_level else region
        econpreds = self.econ_predictors.get(region, None)

        if econpreds is None:
            print(("ERROR: Missing econpreds for %s." % region))
            loggdppc = self.econ_predictors['mean']['loggdppc']
        else:
            loggdppc = econpreds['loggdppc'].get()

        if econpreds is None:
            density = self.econ_predictors['mean']['popop']
        else:
            density = econpreds['popop'].get()

        # If self.covariates==1, baseline_loggdppc cancels out and loggdppc := loggdppc 
        # If self.covariates_scalar != 1, this is equivalent to loggdppc := baseline * exp(growth * time / covariates_scalar)
        if region in self.baseline_loggdppc:
            loggdppc = self.covariates_scalar*(loggdppc - self.baseline_loggdppc[region]) + self.baseline_loggdppc[region]
        else:
            loggdppc = self.covariates_scalar*(loggdppc - self.baseline_loggdppc['mean']) + self.baseline_loggdppc['mean']
                
        return dict(loggdppc=loggdppc, popop=density)

    def get_current(self, region):
        """Get year's economic values for a given region
        Parameters
        ----------
        region : str

        Returns
        -------
        dict
            Output has keys "loggdppc", "logpopop" "year", which give the
            natural log of per capita GDP, the natural log of popop, and
            the year, respectively.
        """
        region = self._get_root_region(region) if self.country_level else region
        econpreds = self.get_econ_predictors(region)
        return dict(loggdppc=econpreds['loggdppc'],
                    logpopop=np.log(econpreds['popop']),
                    year=self.get_yearcovar(region))

    def get_update(self, region, year, ds):
        """
        Parameters
        ----------
        region : str
        year : int
        ds : xarray.Dataset
        """
        assert year < 10000
        region = self._get_root_region(region) if self.country_level else region
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

        return dict(loggdppc=loggdppc, logpopop=np.log(popop), year=self.get_yearcovar(region))

class BinnedEconomicCovariator(EconomicCovariator):
    """Provides income as a series of indicator values for the income bin.

    Parameters
    ----------
    economicmodel : adaptation.SSPEconomicModel
    maxbaseline : int
        Year up to which the covariate baseline is calculated.
    limits : Sequence of float
    country_level : bool, optional
        Whether economic covariators are to be used at the country level.
        If ``True``, any ``region`` str passed into methods will be split on
        ".", and values for the first segment of the split name will be used.
    conf : dict or None, optional
        Configuration dict.
    """
    def __init__(self, economicmodel, maxbaseline, limits, country_level=False, config=None):
        super(BinnedEconomicCovariator, self).__init__(economicmodel, maxbaseline, country_level=country_level, config=config)
        if config is None:
            config = {}
        self.limits = limits

    def add_bins(self, covars):
        """
        Parameters
        ----------
        covars : dict
            A dictionary with keys "loggdppc", "logpopop", and "year", giving 
            the natural log of per capita GDP, the natural log of popop, and
            the year, respectively.
        """
        bin_limits = np.array(self.limits, dtype='float')
        incbin = np.digitize(covars['loggdppc'], bin_limits) # starts at 1
        for ii in range(1, len(self.limits)):
            covars['incbin' + str(ii)] = (incbin == ii)
        return covars
        
    def get_current(self, region):
        """
        Parameters
        ----------
        region : str
        """
        covars = super(BinnedEconomicCovariator, self).get_current(region)
        return self.add_bins(covars)

    def get_update(self, region, year, ds):
        """
        Parameters
        ----------
        region : str
        year : int
        ds : xarray.Dataset
        """
        covars = super(BinnedEconomicCovariator, self).get_update(region, year, ds)
        return self.add_bins(covars)

class ShiftedEconomicCovariator(EconomicCovariator):
    """Provides a 'loggdppc-delta' covariate, which is the loggdppc with a constant subtracted.

    Parameters
    ----------
    economicmodel : adaptation.SSPEconomicModel
    maxbaseline : int
        Year up to which the covariate baseline is calculated.
    country_level : bool, optional
        Whether economic covariators are to be used at the country level.
        If ``True``, any ``region`` str passed into methods will be split on
        ".", and values for the first segment of the split name will be used.
    conf : dict or None, optional
        Configuration dict.
    """
    def __init__(self, economicmodel, maxbaseline, country_level=False, config=None):
        super(ShiftedEconomicCovariator, self).__init__(economicmodel, maxbaseline, country_level=country_level, config=config)
        if config is None:
            config = {}
        assert 'loggdppc-delta' in config, "Must define loggdppc-delta to use loggdppc-shifted."
        self.delta = config['loggdppc-delta']

    def add_shifted(self, covars):
        """Shift `covars['loggdppc']` by subtracting ``self.data``, creating covars['loggdppc-shifted']
        """
        covars['loggdppc-shifted'] = covars['loggdppc'] - self.delta
        return covars
        
    def get_current(self, region):
        """Get year's (shifted) economic values for a given region

        Parameters
        ----------
        region : str

        Returns
        -------
        dict
            Output has keys "loggdppc", "logpopop" "year", which give the
            natural log of per capita GDP, the natural log of popop, and
            the year, respectively. Also includes "loggdppc-shifted", the 
            shifted value.
        """
        covars = super(ShiftedEconomicCovariator, self).get_current(region)
        return self.add_shifted(covars)

    def get_update(self, region, year, ds):
        """Get shifted update

        Parameters
        ----------
        region : str
        year : int
        ds : xarray.Dataset
        """
        covars = super(ShiftedEconomicCovariator, self).get_update(region, year, ds)
        return self.add_shifted(covars)

class MeanWeatherCovariator(Covariator):
    """Provides an average climate variable covariate.

    Parameters
    ----------
    weatherbundle : generate.weather.WeatherBundle
    maxbaseline : int
        Year up to which the covariate baseline is calculated.
    variable : str
        Target weather variable.
    conf : dict or None, optional
        Configuration dict.
    usedaily : bool, optional
    quiet : bool, optional
    """
    def __init__(self, weatherbundle, maxbaseline, variable, config=None, usedaily=True, quiet=False):
        super(MeanWeatherCovariator, self).__init__(maxbaseline, config=config)

        if config is None:
            config = {}
        self.numtempyears = config.get('length', standard_climate_config['length'])
        self.variable = variable

        if not quiet:
            print("Collecting baseline information: Mean of " + variable)
        self.dsvar = variable # Save this to be consistent
            
        temp_predictors = {}
        for region, ds in weatherbundle.baseline_values(maxbaseline, quiet=quiet, only_region=config.get('filter-region')): # baseline through maxbaseline
            self.dsvar = 'daily' + variable if usedaily and 'daily' + variable in ds._variables else variable
            try:
                temp_predictors[region] = averages.interpret(config, standard_climate_config, ds[self.dsvar][-self.numtempyears:])
            except Exception as ex:
                print(("Cannot retrieve baseline data for %s" % variable))
                print(ds)
                raise ex

        self.temp_predictors = temp_predictors
        self.weatherbundle = weatherbundle

        config = configs.search_slowadapt(config)
        config_scale_covariate_changes = config.get('scale-covariate-changes', None)

        baseline_predictors = {}
        for region in temp_predictors:
            baseline_predictors[region] = temp_predictors[region].get()
        self.baseline_predictors = baseline_predictors

        if config_scale_covariate_changes is not None and 'climate' in config_scale_covariate_changes:
            self.covariates_scalar = config_scale_covariate_changes['climate']
        else:
            self.covariates_scalar = 1

        assert self.covariates_scalar > 0, 'scale-covariate-changes should be a strictly positive float'

        self.usedaily = usedaily

    def get_current(self, region):
        """
        This can be called as many times as we want.

        Parameters
        ----------
        region : str
        """
        #assert region in self.temp_predictors, "Missing " + region
        return {self.variable: self.covariates_scalar*(self.temp_predictors[region].get() - self.baseline_predictors[region]) + self.baseline_predictors[region]}

    def get_update(self, region, year, ds):
        """

        Allow ds = None for incadapt farmer who cannot adapt to temperature.

        Parameters
        ----------
        region : str
        year : int
        ds : xarray.Dataset

        Returns
        -------
        dict
        """
        if ds is not None and year > self.startupdateyear:
            self.temp_predictors[region].update(np.mean(ds[self.dsvar]._values)) # if only yearly values

        return {self.variable: self.covariates_scalar*(self.temp_predictors[region].get() - self.baseline_predictors[region]) + self.baseline_predictors[region], 'year': self.get_yearcovar(region)}

class SubspanWeatherCovariator(MeanWeatherCovariator):
    """Provides an average climate variable covariate, using only data from a span of days in each year.

    Parameters
    ----------
    weatherbundle : generate.weather.WeatherBundle
    maxbaseline : int
        Year up to which the covariate baseline is calculated.
    day_start
    day_end
    variable : str
        Target weather variable.
    conf : dict or None, optional
        Configuration dict.
    """
    def __init__(self, weatherbundle, maxbaseline, day_start, day_end, variable, config=None):
        super(SubspanWeatherCovariator, self).__init__(weatherbundle, maxbaseline, variable, config=config)
        if config is None:
            config = {}
        self.maxbaseline = maxbaseline
        self.day_start = day_start
        self.day_end = day_end
        self.all_values = None

        self.mustr = "%smu%d-%d" % (variable, self.day_start, self.day_end)
        self.sigmastr = "%ssigma%d-%d" % (variable, self.day_start, self.day_end)

    def get_current(self, region):
        """

        Parameters
        ----------
        region : str
        """
        if self.all_values is None:
            print(("Collecting " + self.mustr))
            # Read in all regions
            self.all_values = {}
            for year, ds in self.weatherbundle.yearbundles(maxyear=self.maxbaseline, variable_ofinterest=self.variable):
                for region in self.weatherbundle.regions:
                    if region not in self.all_values:
                        self.all_values[region] = np.squeeze(ds[self.variable].sel(region=region).values[self.day_start:self.day_end])
                    else:
                        self.all_values[region] = np.concatenate((self.all_values[region], np.squeeze(ds[self.variable].sel(region=region).values[self.day_start:self.day_end])))

        mu = np.mean(self.all_values[region])
        sigma = np.std(self.all_values[region])

        return {self.mustr: mu, self.sigmastr: sigma}

    def get_update(self, region, year, ds):
        """

        Allow ds = None for incadapt farmer who cannot adapt to temperature.

        Parameters
        ----------
        region : str
        year : int
        ds : xarray.Dataset

        Returns
        -------
        dict
        """
        if self.all_values is None:
            self.get_current(region)
            
        if ds is not None and year > self.startupdateyear:
            self.all_values[region] = np.concatenate((self.all_values[region][(self.day_end - self.day_start):], np.squeeze(ds[self.variable][self.day_start:self.day_end])))

        mu = np.mean(self.all_values[region])
        sigma = np.std(self.all_values[region])

        return {self.mustr: mu, self.sigmastr: sigma}

class SeasonalWeatherCovariator(MeanWeatherCovariator):
    """Provides an average climate variable covariate, using planting and harvesting dates that are IR-specific.

    Parameters
    ----------
    weatherbundle : generate.weather.WeatherBundle
    maxbaseline : int
        Year up to which the covariate baseline is calculated.
    filepath : str
    variable : str
        Target weather variable.
    conf : dict or None, optional
        Configuration dict.
    """
    def __init__(self, weatherbundle, maxbaseline, filepath, variable, config=None):
        super(SeasonalWeatherCovariator, self).__init__(weatherbundle, maxbaseline, variable, config=config)
        if config is None:
            config = {}
        self.maxbaseline = maxbaseline
        assert config['timerate'] == 'month', "Cannot handle daily seasons."
        self.culture_periods = irvalues.get_file_cached(filepath, irvalues.load_culture_months)

        # Setup all averages
        self.byregion = {region: averages.interpret(config, standard_climate_config, []) for region in self.weatherbundle.regions}

        for year, ds in self.weatherbundle.yearbundles(maxyear=self.maxbaseline, variable_ofinterest=self.variable):
            regions = np.array(ds.coords["region"])
            for region, subds in fast_dataset.region_groupby(ds, year, regions, {regions[ii]: ii for ii in range(len(regions))}):
                if region in self.culture_periods:
                    plantii = int(self.culture_periods[region][0] - 1)
                    harvestii = int(self.culture_periods[region][1])
                    self.byregion[region].update(np.mean(subds[self.variable]._values[plantii:harvestii]))

    def get_current(self, region):
        """
        This can be called as many times as we want.

        Parameters
        ----------
        region : str

        Returns
        -------
        dict
        """

        if region in self.culture_periods:
            return {'seasonal' + self.variable: self.byregion[region].get()}
        else:
            return {'seasonal' + self.variable: np.nan}

    def get_update(self, region, year, ds):
        """

        Allow ds = None for incadapt farmer who cannot adapt to temperature.

        Parameters
        ----------
        region : str
        year : int
        ds : xarray.Dataset

        Returns
        -------
        dict
        """
        if ds is not None and year > self.startupdateyear:
            if region in self.culture_periods:
                plantii = int(self.culture_periods[region][0] - 1)
                harvestii = int(self.culture_periods[region][1])
                self.byregion[region].update(np.mean(ds[self.variable]._values[plantii:harvestii]))

        return self.get_current(region)

def get_single_value(numpylike):
    if isinstance(numpylike, xr.DataArray):
        return get_single_value(numpylike.values)
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

    Parameters
    ----------
    yearlyreader
    regions
    baseline_end
    is_historical
    conf : dict or None, optional
        Configuration dict.
    """
    def __init__(self, yearlyreader, regions, baseline_end, is_historical, config=None):
        super(YearlyWeatherCovariator, self).__init__(baseline_end)

        if config is None:
            config = {}
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
        """
        This can be called as many times as we want.

        Parameters
        ----------
        region : str

        Return
        ------
        dict
        """
        return {self.yearlyreader.get_dimension()[0]: self.predictors[region].get()}

    def get_update(self, region, year, ds):
        """

        Parameters
        ----------
        region : str
        year : int
        ds : xarray.Dataset

        Returns
        -------
        dict
        """
        if self.is_historical or ds is None:
            return self.get_current(region)

        assert year < 10000

        values = self.random_year_access.get_year(year).sel(region=region)
        self.predictors[region].update(values)

        return {self.yearlyreader.get_dimension()[0]: self.predictors[region].get()}

class MeanBinsCovariator(Covariator):
    """Provides binned weather data.

    This class has not been updated to reflect xarray use.
    
    Parameters
    ----------
    weatherbundle : generate.weather.WeatherBundle
    binlimits
    dropbin
    maxbaseline : int
        Year up to which the covariate baseline is calculated.
    conf : dict or None, optional
        Configuration dict.
    quiet : bool, optional
    """
    def __init__(self, weatherbundle, binlimits, dropbin, maxbaseline, config=None, quiet=False):
        super(MeanBinsCovariator, self).__init__(maxbaseline)

        if config is None:
            config = {}
        self.binlimits = binlimits
        self.dropbin = dropbin
        self.numtempyears = config.get('length', standard_climate_config['length'])

        if not quiet:
            print("Collecting baseline information: Bins")
        temp_predictors = {} # {region: [rm-bin-1, ...]}
        for region, binyears in weatherbundle.baseline_values(maxbaseline, quiet=quiet, only_region=config.get('filter-region')): # baseline through maxbaseline
            usedbinyears = []
            for kk in range(binyears.shape[-1]):
                usedbinyears.append(averages.interpret(config, standard_climate_config, binyears[-self.numtempyears:, kk]))
            temp_predictors[region] = usedbinyears

        self.temp_predictors = temp_predictors
        self.weatherbundle = weatherbundle

    def get_current(self, region):
        """
        This can be called as many times as we want.

        Parameters
        ----------
        region : str

        Returns
        -------
        dict
        """
        #assert region in self.temp_predictors, "Missing " + region
        assert len(self.weatherbundle.get_dimension()) == len(self.temp_predictors[region])
        return {self.weatherbundle.get_dimension()[ii]: self.temp_predictors[region][ii].get() for ii in range(len(self.weatherbundle.get_dimension()))}

    def get_update(self, region, year, ds):
        """

        Parameters
        ----------
        region : str
        year : int
        ds : xarray.Dataset
        """
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
    """Provides the share of the population in each age group.

    Parameters
    ----------
    economicmodel : adaptation.SSPEconomicModel
    maxbaseline : int
        Year up to which the covariate baseline is calculated.
    conf : dict or None, optional
        Configuration dict.
    """
    def __init__(self, economicmodel, maxbaseline, config=None):
        super(AgeShareCovariator, self).__init__(maxbaseline)

        if config is None:
            config = {}
        self.config = config

        self.ageshares = agecohorts.load_ageshares(economicmodel.model, economicmodel.scenario)
        self.economicmodel = economicmodel

        self.agerm = {}
        self.get_current('mean') # Fill in the mean agerm

    def get_current(self, region):
        """
        This can be called as many times as we want.

        Parameters
        ----------
        region : str

        Returns
        -------
        dict
        """
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
        """

        Parameters
        ----------
        region : str
        year : int
        ds : xarray.Dataset

        Returns
        -------
        dict
        """
        region = region[:3] # Just country code
        if region not in self.ageshares:
            region = 'mean' # XXX: This updates for every country!

        if region in self.agerm:
            if year in self.ageshares[region]:
                for cc in range(len(agecohorts.columns)):
                    self.agerm[region][agecohorts.columns[cc]].update(self.ageshares[region][year][cc])

        return {column: self.agerm[region][column].get() for column in agecohorts.columns}

class ConstantCovariator(Covariator):
    """Provides an IR-specific value that is constant across time.

    Parameters
    ----------
    name : str
    irvalues
    """
    def __init__(self, name, irvalues):
        super(ConstantCovariator, self).__init__(None)
        self.name = name
        self.irvalues = irvalues

    def get_current(self, region):
        """

        Parameters
        ----------
        region : str

        Returns
        -------
        dict
        """
        return {self.name: self.irvalues[region]}

    def get_update(self, region, year, ds):
        """

        Parameters
        ----------
        region : str
        year : int
        ds : xarray.Dataset

        Returns
        -------
        dict
        """
        return {self.name: self.irvalues[region]}

def populate_constantcovariator_by_hierid(covar_name, parent_hierids, hi_df=None):
    """Return ConstantCovariator with 1.0 for IRs falling in `parent_hierids`

    Parameters
    ----------
    covar_name : str
        Covariator name. Generally starts with 'hierid*'.
    parent_hierids : Sequence of str
        Hierids we want to see if impact regions (IR) fall within. These are 
        defined in a magical hierarchy.csv file.
    hi_df : pandas.DataFrame or None, optional
        Optional DataFrame of hierarchical region relationships. Must index 
        'region-key', with column 'parent-key' populated with str. If None,
        parses /shares/gcp/regions/hierarchy.csv from sharedpath. This is 
        useful for testing and debugging.

    Returns
    -------
    ConstantCovariator
        Has binary floats assigned to each IR. 1.0 if within 'parent_hierids',
        otherwise 0.0.
    """
    target_regions = list(parent_hierids)

    if hi_df is None:
        hi_df = read_csv(files.sharedpath('regions/hierarchy.csv'),
                        skiprows=31, index_col='region-key')

    # 1.0 if in hierid(s), otherwise *always* 0.0, even if bad key.
    ir_dict = defaultdict(lambda: 0.0)
    for r in hi_df.index.values:
        if irregions.contains_region(target_regions, r, hi_df):
            ir_dict[r] = 1.0

    return ConstantCovariator(covar_name, ir_dict)

class CombinedCovariator(Covariator):
    """Reports all covariates provided by a collection of Covariator objects.
    
    Parameters
    ----------
    covariators : Sequence of adaptation.covariates.Covariator
    """
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
        """

        Parameters
        ----------
        region : str

        Returns
        -------
        dict
        """
        result = {}
        for covariator in self.covariators:
            subres = covariator.get_current(region)
            for key in subres:
                result[key] = subres[key]

        return result

    def get_update(self, region, year, ds):
        """

        Parameters
        ----------
        region : str
        year : int
        ds : xarray.Dataset
        """
        result = {}
        for covariator in self.covariators:
            subres = covariator.get_update(region, year, ds)
            for key in subres:
                result[key] = subres[key]

        return result

class TranslateCovariator(Covariator):
    """Rename or otherwise transform the results of another Covariator.

    Parameters
    ----------
    covariator : adaptation.covariates.Covariator
    renames
    transforms : dict or None, optional
    """
    def __init__(self, covariator, renames, transforms=None):
        super(TranslateCovariator, self).__init__(covariator.startupdateyear)
        if transforms is None:
            transforms = {}
        self.covariator = covariator
        self.renames = renames
        self.transforms = transforms

    def translate(self, covariates):
        """

        Parameters
        ----------
        covariates : dict

        Returns
        -------
        result : dict
        """
        result = {}
        for newname in self.renames:
            oldname = self.renames[newname]
            result[newname] = self.transforms.get(newname, lambda x: x)(covariates[oldname])

        return result

    def get_current(self, region):
        """

        Parameters
        ----------
        region : str
        """
        baseline = self.covariator.get_current(region)
        return self.translate(baseline)

    def get_update(self, region, year, ds):
        """

        Parameters
        ----------
        region : str
        year : int
        ds : xarray.Dataset
        """
        update = self.covariator.get_update(region, year, ds)
        return self.translate(update)

class SplineCovariator(TranslateCovariator):
    """Convert a simple covariator into a series of spline segments.
    Each spline segment is defined as (x - l_k) * (x >= l_k) for some l_k.

    `covariator` should be a Covariator, returning dictionaries
    containing the covariate to be turned into a spline.

    The resulting spline covariate dictionary will contain keys of
    the form `[covarname][suffix][k]`, for `k` in 1 ... len(leftlimits).
        
    Parameters
    ----------
    covariator : Covariator 
        Source for variable to be splined.
    suffix : str
        Added to the covariate name when reporting splines.
    leftlimits : list-like of numeric
        The values for l_k as defined above.

    """
    def __init__(self, covariator, suffix, leftlimits):
        super(SplineCovariator, self).__init__(covariator, {})
        self.suffix = suffix
        self.leftlimits = leftlimits

    def translate(self, covariates):
        """

        Parameters
        ----------
        covariates : dict

        Returns
        -------
        result : dict
        """
        result = {}
        for covarname in covariates:
            for ii in range(len(self.leftlimits)):
                if covariates[covarname] - self.leftlimits[ii] < 0:
                    result[covarname + self.suffix + str(ii+1)] = 0
                    result[covarname + 'indic' + str(ii+1)] = 0
                else:
                    result[covarname + self.suffix + str(ii+1)] = covariates[covarname] - self.leftlimits[ii]
                    result[covarname + 'indic' + str(ii+1)] = 1
        return result

class ClipCovariator(TranslateCovariator):
    """Clip covariate values at a high and low value.

    `covariator` should be a Covariator, returning dictionaries
    containing the covariate to be clipped.

    The resulting covariate dictionary will contain this covarname,
    but with values clipped to be between the high and low bounds.
        
    Parameters
    ----------
    covariator : Covariator 
        Source for variable to be splined.
    cliplow : float
        clip values to be max(cliplow, baseline)
    cliphigh : float
        clip values to be min(cliphigh, baseline)

    """
    def __init__(self, covariator, cliplow, cliphigh):
        super(ClipCovariator, self).__init__(covariator, {})
        self.cliplow = cliplow
        self.cliphigh = cliphigh

    def translate(self, covariates):
        """
        Parameters
        ----------
        covariates : dict

        Returns
        -------
        result : dict
        """
        for covarname in covariates:
            if covariates[covarname] < self.cliplow:
                covariates[covarname] = self.cliplow
            elif covariates[covarname] > self.cliphigh:
                covariates[covarname] = self.cliphigh

        return covariates

class CountryAggregatedCovariator(Covariator):
    """Spatially average the covariates across all regions within a country.

    Parameters
    ----------
    source
    regions
    """
    def __init__(self, source, regions):
        self.source = source
        bycountry = {}
        for region in regions:
            # Should replace much of this with a DefaultDict...
            if region[:3] in bycountry:
                bycountry[region[:3]].append(region)
            else:
                bycountry[region[:3]] = [region]
        self.bycountry = bycountry

    def get_current(self, country):
        """

        Parameters
        ----------
        country : str

        Returns
        -------
        dict
        """
        values = [self.source.get_current(region) for region in self.bycountry[country]]
        return {key: np.mean([value[key] for value in values]) for key in values[0]}

class CountryDeviationCovariator(CountryAggregatedCovariator):
    """Report the deviation between a region-specific covariate and its country average.
    """
    def get_current(self, region):
        """

        Parameters
        ----------
        region : str

        Returns
        -------
        dict
        """
        countrylevel = super(CountryDeviationCovariator, self).get_current(region[:3])
        subcountrylevel = self.source.get_current(region)

        return {key: subcountrylevel[key] - countrylevel[key] for key in subcountrylevel}

class HistoricalCovariator(Covariator):
    """Just don't ignore get_update; note that this means that the source
    covariator should not be used elsewhere where it might have get_update
    called.

    Parameters
    ----------
    source
    suffix
    """
    def __init__(self, source, suffix):
        super(HistoricalCovariator, self).__init__(source.startupdateyear)
        self.source = source
        self.suffix = suffix

    def get_update(self, region, year, ds):
        """

        Parameters
        ----------
        region : str
        year : int
        ds : xarray.Dataset
        """
        return self.get_current(region)

    def get_current(self, region):
        """

        Parameters
        ----------
        region : str
        """
        covariates = self.source.get_current(region)
        return {covar + self.suffix: covariates[covar] for covar in covariates}

class ProductCovariator(Covariator):
    """Multiple the covariates provided by two other Covariators.

    Parameters
    ----------
    source1 : Covariator
    source2 : Covariator
    """
    def __init__(self, source1, source2):
        assert source1.startupdateyear == source2.startupdateyear
        super(ProductCovariator, self).__init__(source1.startupdateyear)
        self.source1 = source1
        self.source2 = source2

    def make_product(self, covars1, covars2):
        """

        Parameters
        ----------
        covars1 : dict
        covars2 : dict

        Returns
        -------
        dict
        """
        combos = itertools.product(list(covars1.keys()), list(covars2.keys()))
        result = {"%s*%s" % (key1, key2): covars1[key1] * covars2[key2] for key1, key2 in combos}
        if 'year' in covars1:
            result['year'] = covars1['year']
        if 'year' in covars2:
            result['year'] = covars2['year']
        return result
        
    def get_update(self, region, year, ds):
        """

        Parameters
        ----------
        region : str
        year : int
        ds : xarray.Dataset
        """
        covars1 = self.source1.get_update(region, year, ds)
        covars2 = self.source2.get_update(region, year, ds)
        return self.make_product(covars1, covars2)

    def get_current(self, region):
        """

        Parameters
        ----------
        region : str
        """
        covars1 = self.source1.get_current(region)
        covars2 = self.source2.get_current(region)
        return self.make_product(covars1, covars2)
    
class PowerCovariator(Covariator):
    """Raise a covariate provided by another Covariator to a power.
    
    Parameters
    ----------
    source
    power : float or int
    """
    def __init__(self, source, power):
        super(PowerCovariator, self).__init__(source.startupdateyear)
        self.source = source
        self.power = power

    def make_power(self, covars):
        """

        Parameters
        ----------
        covars : dict

        Returns
        -------
        dict
        """
        return {"%s^%g" % (key, self.power): covars[key] ** self.power for key in covars}
        
    def get_update(self, region, year, ds):
        """

        Parameters
        ----------
        region : str
        year : int
        ds : xarray.Dataset
        """
        covars = self.source.get_update(region, year, ds)
        return self.make_power(covars)

    def get_current(self, region):
        """
        This can be called as many times as we want.

        Parameters
        ----------
        region : str
        """
        covars = self.source.get_current(region)
        return self.make_power(covars)
