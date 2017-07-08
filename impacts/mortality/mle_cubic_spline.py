import csv, copy
import numpy as np
from adaptation import csvvfile, curvegen, curvegen_arbitrary, covariates
from generate import caller
from openest.models.curve import CubicSplineCurve
from openest.generate.stdlib import *
from openest.generate import diagnostic
from impactcommon.math import minspline

knots = [-12, -7, 0, 10, 18, 23, 28, 33]

def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full'):
    """Computes f(x_t | \theta(z_t)) - f(x_0 | \theta(z_t)), where f is
    the adaptation-estimated cubic spline, x_t is the set of weather
    predictors, and \theta(z_t) relates how the set of parameters that
    determine the cubic spline depend on covariates z_t.  I currently
    need to create two covariate instances, so that it doesn't get
    updated twice in the calculation.
    """

    covariator = covariates.CombinedCovariator([covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 15, 2015, varindex=0), {'climtas': 'tas_sum'}, {'climtas': lambda x: x / 365}),
                                                covariates.EconomicCovariator(economicmodel, 1, 2015)])
    covariator2 = covariates.CombinedCovariator([covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 15, 2015, varindex=0), {'climtas': 'tas_sum'}, {'climtas': lambda x: x / 365}),
                                                 covariates.EconomicCovariator(economicmodel, 1, 2015)])

    csvvfile.collapse_bang(csvv, qvals.get_seed())

    curr_curvegen = curvegen_arbitrary.MLECoefficientsCurveGenerator(lambda coeffs: CubicSplineCurve(knots, coeffs),
                                                        ['C'] + ['C^3'] * (len(knots) - 2),
                                                        '100,000 * death/population', 'spline_variables-', len(knots) - 1, csvv)
    farm_curvegen = curvegen.FarmerCurveGenerator(curr_curvegen, covariator, farmer)

    # Determine minimum value of curve between 10C and 25C
    print "Determining minimum temperatures."
    with open(caller.callinfo['splineminpath'], 'w') as fp:
        writer = csv.writer(fp)
        writer.writerow(['region', 'brute', 'analytic'])
        baselinemins = {}
        for region in weatherbundle.regions:
            curve = curr_curvegen.get_curve(region, covariator.get_current(region))
            temps = np.arange(10, 26)
            mintemp = temps[np.argmin(curve(temps))]
            mintemp2 = minspline.findsplinemin(knots, curve.coeffs, 10, 25)
            if np.abs(mintemp - mintemp2) > 1:
                print "WARNING: %s has unclear mintemp: %f, %f" % (region, mintemp, mintemp2)
            baselinemins[region] = mintemp2
            writer.writerow([region, mintemp, mintemp2])
    print "Finishing calculation setup."

    # Generating all curves, for baseline
    baseline_loggdppc = {}
    for region in weatherbundle.regions:
        baseline_loggdppc[region] = covariator.get_current(region)['loggdppc']

    loggdppc_marginals = curr_curvegen.get_marginals('loggdppc')
    loggdppc_marginals = np.array([loggdppc_marginals[predname] for predname in curr_curvegen.prednames]) # same order as temps
    print "MARGINALS"
    print loggdppc_marginals

    def coeff_getter_positive(region, year, temps, curve):
        return curve.curr_curve.coeffs

    def coeff_getter_negative(region, year, temps, curve):
        return curve.curr_curve.coeffs

    maineffect = YearlyCoefficients('100,000 * death/population', farm_curvegen, "the mortality response curve", coeff_getter_positive)

    # Subtract off result at 20C; currently need to reproduce adapting curve
    negcsvv = copy.copy(csvv)
    negcsvv['gamma'] = [-csvv['gamma'][ii] if csvv['covarnames'][ii] == '1' else csvv['gamma'][ii] for ii in range(len(csvv['gamma']))]

    negcurr_curvegen = curvegen_arbitrary.MLECoefficientsCurveGenerator(lambda coeffs: CubicSplineCurve(knots, coeffs),
                                                                     ['C'] + ['C^3'] * (len(knots) - 2),
                                                                     '100,000 * death/population', 'spline_variables-', len(knots) - 1, negcsvv)
    negfarm_curvegen = curvegen.FarmerCurveGenerator(negcurr_curvegen, covariator2, farmer, save_curve=False)
    baseeffect = YearlyCoefficients('100,000 * death/population', negfarm_curvegen, 'offset to normalize to 20 C', coeff_getter_negative, weather_change=lambda region, temps: 365 * np.array(CubicSplineCurve(knots, np.zeros(len(knots)-1)).get_terms(baselinemins[region])))

    # Collect all baselines
    calculation = Transform(Sum([maineffect, baseeffect]),
                            '100,000 * death/population', 'deaths/person/year', lambda x: x / 1e5,
                            'convert to deaths/person/year', "Divide by 100000 to convert to deaths/person/year.")

    return calculation, [], covariator.get_current
