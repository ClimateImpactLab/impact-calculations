import csv, copy
import numpy as np
from adaptation import csvvfile, curvegen, curvegen_arbitrary, curvegen_known, covariates
from generate import caller
from interpret import configs
from openest.models.curve import ZeroInterceptPolynomialCurve
from openest.generate.stdlib import *
from openest.generate import diagnostic
from impactcommon.math import minpoly

def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full', config={}):
    """Computes f(x_t | \theta(z_t)) - f(x_0 | \theta(z_t)), where f is
    the adaptation-estimated polynomial, x_t is the set of weather
    predictors, and \theta(z_t) relates how the set of parameters that
    determine the polynomial depend on covariates z_t.  I currently
    need to create two covariate instances, so that it doesn't get
    updated twice in the calculation.
    """

    covariator = covariates.CombinedCovariator([covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 2015, config=configs.merge(config, 'climcovar'), varindex=0), {'climtas': 'tas'}),
                                                covariates.EconomicCovariator(economicmodel, 2015, config=configs.merge(config, 'econcovar'))])
    covariator2 = covariates.CombinedCovariator([covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 2015, config=configs.merge(config, 'climcovar'), varindex=0), {'climtas': 'tas'}),
                                                 covariates.EconomicCovariator(economicmodel, 2015, config=configs.merge(config, 'econcovar'))])

    curr_curvegen = curvegen_known.PolynomialCurveGenerator(['C'] + ['C^%d' % pow for pow in range(2, order+1)],
                                                            '100,000 * death/population', 'tas', order, csvv)

    farm_curvegen = curvegen.FarmerCurveGenerator(curr_curvegen, covariator, farmer)

    # Generating all curves, for baseline
    baseline_loggdppc = {}
    for region in weatherbundle.regions:
        baseline_loggdppc[region] = covariator.get_current(region)['loggdppc']

    # Determine minimum value of curve between 10C and 25C
    baselinecurves, baselinemins = constraints.get_curve_minima(weatherbundle.regions, curr_curvegen, covariator, config.get('clip-mintemp', 10), config.get('clip-maxtemp', 25),
                                                                lambda region, curve: minpoly.findpolymin([0] + curve.ccs, config.get('clip-mintemp', 10), config.get('clip-maxtemp', 25)))
    
    climtas_marginals = curr_curvegen.get_marginals('climtas')
    climtas_marginals = np.array([climtas_marginals[predname] for predname in curr_curvegen.prednames]) # same order as temps
    print "MARGINALS"
    print climtas_marginals

    def coeff_getter_positive(region, year, temps, curve):
        return curve.curr_curve.coeffs

    def coeff_getter_negative(region, year, temps, curve):
        return curve.curr_curve.coeffs

    maineffect = YearlyCoefficients('100,000 * death/population', farm_curvegen, "the mortality response curve", coeff_getter_positive)

    # Subtract off result at 20C; currently need to reproduce adapting curve
    negcsvv = copy.copy(csvv)
    negcsvv['gamma'] = [-csvv['gamma'][ii] if csvv['covarnames'][ii] == '1' else csvv['gamma'][ii] for ii in range(len(csvv['gamma']))]

    negcurr_curvegen = curvegen_arbitrary.MLECoefficientsCurveGenerator(lambda coeffs: ZeroInterceptPolynomialCurve(coeffs)
                                                                        ['C'] + ['C^%d' % pow for pow in range(2, order+1)],
                                                                        '100,000 * death/population', 'tas', order, negcsvv)
    negfarm_curvegen = curvegen.FarmerCurveGenerator(negcurr_curvegen, covariator2, farmer, save_curve=False)
    baseeffect = YearlyCoefficients('100,000 * death/population', negfarm_curvegen, 'offset to normalize to 20 C', coeff_getter_negative, weather_change=lambda region, temps: 365 * np.array(CubicSplineCurve(knots, np.zeros(len(knots)-1)).get_terms(baselinemins[region])))

    # Collect all baselines
    calculation = Transform(Sum([maineffect, baseeffect]),
                            '100,000 * death/population', 'deaths/person/year', lambda x: x / 1e5,
                            'convert to deaths/person/year', "Divide by 100000 to convert to deaths/person/year.")

    return calculation, [], covariator.get_current
