import re
import numpy as np
from adaptation import csvvfile, curvegen, curvegen_arbitrary, covariates
from openest.models.curve import CubicSplineCurve
from openest.generate.stdlib import *

knots = [-12, -7, 0, 10, 18, 23, 28, 33]

def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full'):
    covariator = covariates.CombinedCovariator([covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 15, 2015), {'climtas': 'tas_sum'}, {'climtas': lambda x: x / 365}),
                                                covariates.EconomicCovariator(economicmodel, 3, 2015)])

    csvvfile.collapse_bang(csvv, qvals.get_seed())

    curr_curvegen = curvegen_arbitrary.CoefficientsCurveGenerator(lambda coeffs: CubicSplineCurve(knots, coeffs),
                                                        ['C'] + ['C^3'] * (len(knots) - 2),
                                                        '100,000 * death/population', 'spline_variables-', len(knots) - 1, csvv)
    farm_curvegen = curvegen.FarmerCurveGenerator(curr_curvegen, covariator, farmer)

    # Collect all baselines
    calculation = Transform(
        YearlyCoefficients('100,000 * death/population', farm_curvegen, "the mortality response curve",
                           lambda curve: curve.curr_curve.coeffs),
        '100,000 * death/population', 'deaths/person/year', lambda x: x / 1e5,
        'convert to deaths/person/year', "Divide by 100000 to convert to deaths/person/year.")

    return calculation, [], covariator.get_baseline_args
