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
    return weather.iterate_bundles(discover_variable(files.sharedpath('climate/BCSD/aggregation/cmip5/IR_level'), 'tas'))

def produce(targetdir, weatherbundle, economicmodel, get_model, pvals, do_only=None, country_specific=True, result_callback=None, push_callback=None, suffix='', do_farmers=False, profile=False, redocheck=False, diagnosefile=False):
    predgen = covariates.CombinedCovariator([covariates.MeanWeatherCovariator(weatherbundle, 15, 2015),
                                             covariates.EconomicCovariator(economicmodel, 3, 2015)])
    covars = ['tas', 'loggdppc', 'logpopop']

    curvegen = RecursiveInstantaneousCurveGenerator(None, None, predgen, lambda predictors: FlatCurve([predictors[covar] for covar in covars]))
    calculation = ApplyCurve(curvegen, ['C', 'logUSD', 'loppk'], covars,
                             ['Mean temperature', 'log GDP per capita', 'Log population-weighted population density'],
                             ['Last 15 years of temperature', 'Estimate GDP per capita', 'Population density, as weighted by population'])

    effectset.write_ncdf(targetdir, 'Covariates', weatherbundle, calculation, None, "Extensive margin labor impacts, with interpolation and adaptation through interpolation.", weatherbundle.dependencies + economicmodel.dependencies)
