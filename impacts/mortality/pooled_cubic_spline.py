import numpy as np
from adaptation import csvvfile, curvegen, curvegen_arbitrary, covariates
from openest.models.curve import CubicSplineCurve
from openest.generate.stdlib import *
from openest.generate import diagnostic

knots = [-12, -7, 0, 10, 18, 23, 28, 33]

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

    maineffect = YearlyCoefficients('100,000 * death/population', farm_curvegen, "the mortality response curve",
                                    lambda curve: curve.curr_curve.coeffs)

    # Determine minimum value of curve between 10C and 25C
    baselinemins = {}
    for region in weatherbundle.regions:
        curve = curr_curvegen.get_curve(region, covariator.get_baseline(region))
        temps = np.arange(10, 26)
        mintemp = temps[np.argmin(curve(temps))]
        baselinemins[region] = mintemp
        if diagnostic.is_recording():
            diagnostic.record(region, 2015, 'mintemp', mintemp)

    # Subtract off result at 20C; currently need to reproduce adapting curve
    negcsvv = copy.copy(csvv)
    negcsvv['gamma'] = -csvv['gamma']

    negcurr_curvegen = curvegen_arbitrary.CoefficientsCurveGenerator(lambda coeffs: CubicSplineCurve(knots, coeffs),
                                                                     ['C'] + ['C^3'] * (len(knots) - 2),
                                                                     '100,000 * death/population', 'spline_variables-', len(knots) - 1, negcsvv)
    negfarm_curvegen = curvegen.FarmerCurveGenerator(negcurr_curvegen, covariator2, farmer, save_curve=False)
    baseeffect = YearlyCoefficients('100,000 * death/population', negfarm_curvegen, 'offset to normalize to 20 C', lambda curve: curve.curr_curve.coeffs, weather_change=lambda region, temps: 365 * np.array(CubicSplineCurve(knots, np.zeros(len(knots)-1)).get_terms(baselinemins[region])))

    # Collect all baselines
    calculation = Transform(Positive(Sum([maineffect, baseeffect])),
                            '100,000 * death/population', 'deaths/person/year', lambda x: x / 1e5,
                            'convert to deaths/person/year', "Divide by 100000 to convert to deaths/person/year.")

    return calculation, [], covariator.get_baseline
