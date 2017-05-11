import csv, copy
import numpy as np
from adaptation import csvvfile, curvegen, curvegen_arbitrary, covariates, constraints
from generate import caller
from openest.models.curve import CubicSplineCurve
from openest.generate.stdlib import *
from openest.generate import diagnostic
from impactcommon.math import minspline

knots = [-10, 0, 10, 20, 28, 33]

def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full'):
    covariator = covariates.CombinedCovariator([covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 15, 2015, varindex=0), {'climtas': 'tas_sum'}, {'climtas': lambda x: x / 365}),
                                                covariates.EconomicCovariator(economicmodel, 3, 2015)])
    covariator2 = covariates.CombinedCovariator([covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 15, 2015, varindex=0), {'climtas': 'tas_sum'}, {'climtas': lambda x: x / 365}),
                                                 covariates.EconomicCovariator(economicmodel, 3, 2015)])

    csvvfile.collapse_bang(csvv, qvals.get_seed())

    curr_curvegen = curvegen_arbitrary.CoefficientsCurveGenerator(lambda coeffs: CubicSplineCurve(knots, coeffs),
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
            baselinemins[region] = 365 * np.array(CubicSplineCurve(knots, None).get_terms(baselinemins[region]))
            writer.writerow([region, mintemp, mintemp2])
    print "Finishing calculation setup."

    maineffect = YearlyCoefficients('100,000 * death/population', farm_curvegen, "the mortality response curve",
                                    constraints.make_get_coeff_goodmoney(weatherbundle, covariator, curr_curvegen,
                                                                         baselinemins, lambda curve: curve.curr_curve.coeffs))

    # Subtract off result at 20C; currently need to reproduce adapting curve
    negcsvv = copy.copy(csvv)
    negcsvv['gamma'] = -csvv['gamma']

    negcurr_curvegen = curvegen_arbitrary.CoefficientsCurveGenerator(lambda coeffs: CubicSplineCurve(knots, coeffs),
                                                                     ['C'] + ['C^3'] * (len(knots) - 2),
                                                                     '100,000 * death/population', 'spline_variables-', len(knots) - 1, negcsvv)
    negfarm_curvegen = curvegen.FarmerCurveGenerator(negcurr_curvegen, covariator2, farmer, save_curve=False)
    baseeffect = YearlyCoefficients('100,000 * death/population', negfarm_curvegen, 'offset to normalize to 20 C',
                                    constraints.make_get_coeff_goodmoney(weatherbundle, covariator, curr_curvegen,
                                                                         baselinemins, lambda curve: curve.curr_curve.coeffs, flipsign=True),
                                    weather_change=lambda region, temps: baselinemins[region])

    # Collect all baselines
    calculation = Transform(Positive(Sum([maineffect, baseeffect])),
                            '100,000 * death/population', 'deaths/person/year', lambda x: x / 1e5,
                            'convert to deaths/person/year', "Divide by 100000 to convert to deaths/person/year.")

    return calculation, [], covariator.get_current