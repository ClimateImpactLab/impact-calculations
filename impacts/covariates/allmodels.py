from generate import weather, effectset
from helpers import files
from climate.discover import discover_variable
from adaptation import covariates
from openest.generate.curvegen import RecursiveInstantaneousCurveGenerator
from openest.generate.daily import ApplyCurve
from openest.models.curve import FlatCurve

def preload():
    pass

def get_bundle_iterator():
    return weather.iterate_combined_bundles(discover_variable(files.sharedpath('climate/BCSD/aggregation/cmip5/IR_level'), 'tas'),
                                            discover_variable(files.sharedpath('climate/BCSD/aggregation/cmip5/IR_level'), 'pr'))

def produce(targetdir, weatherbundle, economicmodel, get_model, pvals, do_only=None, country_specific=True, result_callback=None, push_callback=None, suffix='', do_farmers=False, profile=False, redocheck=False, diagnosefile=False):
    predgen = covariates.CombinedCovariator([covariates.SeasonalWeatherCovariator(weatherbundle.get_subset(0), 15, 2015, 0, 90),
                                             covariates.SeasonalWeatherCovariator(weatherbundle.get_subset(0), 15, 2015, 180, 270),
                                             covariates.SeasonalWeatherCovariator(weatherbundle.get_subset(1), 15, 2015, 0, 90),
                                             covariates.SeasonalWeatherCovariator(weatherbundle.get_subset(1), 15, 2015, 180, 270),
                                             covariates.EconomicCovariator(economicmodel, 3, 2015)])
    covars = ['tasmu0-90', 'tassigma0-90', 'tasmu180-270', 'tassigma180-270', 'prmu0-90', 'prsigma0-90',
              'prmu180-270', 'prsigma180-270', 'loggdppc', 'logpopop']

    curvegen = RecursiveInstantaneousCurveGenerator(None, None, predgen, lambda predictors: FlatCurve([predictors[covar] for covar in covars]))
    calculation = ApplyCurve(curvegen, ['C', 'C', 'C', 'C', 'm', 'm', 'm', 'm', 'logUSD', 'loppk'], covars,
                             ['Mean winter temperature', 'Winter temperature range', 'Mean summer temperature', 'Summer temperature range', 'Mean winter precipitation', 'Winter precipitation range', 'Mean summer precipitation', 'Summer precipitation range', 'log GDP per capita', 'Log population-weighted population density'],
                             ['Mean across last 15 years of winter temperature',
                              'Standard deviation across last 15 years of winter temperature',
                              'Mean across last 15 years of summer temperature',
                              'Standard deviation across last 15 years of summer temperature',
                              'Mean across last 15 years of winter precipitation',
                              'Standard deviation across last 15 years of winter precipitation',
                              'Mean across last 15 years of summer precipitation',
                              'Standard deviation across last 15 years of summer precipitation',
                              'Estimate GDP per capita',
                              'Population density, as weighted by population'])

    effectset.write_ncdf(targetdir, 'Covariates', weatherbundle, calculation, None, "Extensive margin labor impacts, with interpolation and adaptation through interpolation.", weatherbundle.dependencies + economicmodel.dependencies, suffix=suffix)
