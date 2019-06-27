from generate import weather, effectset
from impactlab_tools.utils import files
from climate.discover import discover_variable
from adaptation import covariates
from openest.generate.curvegen import FunctionCurveGenerator
from openest.generate.daily import ApplyCurve
from openest.models.curve import FlatCurve

do_singleyear = True

def preload():
    pass

def get_bundle_iterator(config):
    return weather.iterate_bundles(discover_variable(files.sharedpath('climate/BCSD/aggregation/cmip5/IR_level'), 'tas'),
                                   discover_variable(files.sharedpath('climate/BCSD/aggregation/cmip5/IR_level'), 'pr'))

def produce(targetdir, weatherbundle, economicmodel, pvals, config, result_callback=None, push_callback=None, suffix='', profile=False, diagnosefile=False):
    if do_singleyear:
        covar_config = dict(length=1)
    else:
        covar_config = {}

    predgen = covariates.CombinedCovariator([covariates.MeanWeatherCovariator(weatherbundle, 2015, 'tas', config),
                                             covariates.SubspanWeatherCovariator(weatherbundle, 2015, 0, 90, 'tas', config),
                                             covariates.SubspanWeatherCovariator(weatherbundle, 2015, 180, 270, 'tas', config),
                                             covariates.SubspanWeatherCovariator(weatherbundle, 2015, 0, 90, 'pr', config),
                                             covariates.SubspanWeatherCovariator(weatherbundle, 2015, 180, 270, 'pr', config),
                                             covariates.EconomicCovariator(economicmodel, 2015, config)])
    covars = ['tas', 'tasmu0-90', 'tassigma0-90', 'tasmu180-270', 'tassigma180-270', 'prmu0-90', 'prsigma0-90',
              'prmu180-270', 'prsigma180-270', 'loggdppc', 'logpopop']

    curvegen = FunctionCurveGenerator(None, None, predgen, lambda covariates: FlatCurve([covariates[covar] for covar in covars]))
    calculation = ApplyCurve(curvegen, ['C', 'C', 'C', 'C', 'C', 'm', 'm', 'm', 'm', 'logUSD', 'loppk'], covars,
                             ['Mean yearly temperature', 'Mean winter temperature', 'Winter temperature range', 'Mean summer temperature', 'Summer temperature range', 'Mean winter precipitation', 'Winter precipitation range', 'Mean summer precipitation', 'Summer precipitation range', 'log GDP per capita', 'Log population-weighted population density'],
                             ['Mean across last 15 years of daily temperature',
                              'Mean across last 15 years of winter temperature',
                              'Standard deviation across last 15 years of winter temperature',
                              'Mean across last 15 years of summer temperature',
                              'Standard deviation across last 15 years of summer temperature',
                              'Mean across last 15 years of winter precipitation',
                              'Standard deviation across last 15 years of winter precipitation',
                              'Mean across last 15 years of summer precipitation',
                              'Standard deviation across last 15 years of summer precipitation',
                              'Estimate GDP per capita',
                              'Population density, as weighted by population'])

    effectset.generate(targetdir, 'Covariates' + suffix, weatherbundle, calculation, "Extensive margin labor impacts, with interpolation and adaptation through interpolation.", weatherbundle.dependencies + economicmodel.dependencies, config)
