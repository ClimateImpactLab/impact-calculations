import re
import numpy as np
from adaptation import csvvfile, curvegen, curvegen_step, covariates
from openest.models.curve import CubicSplineCurve
from openest.generate.stdlib import *

knots = [-12, -7, 0, 10, 18, 23, 28, 33]

def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full'):
    covariator = covariates.CombinedCovariator([covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 15, 2015), {'tas_sum': 'climtas'}, {'tas_sum': lambda x: x / 365}),
                                                covariates.EconomicCovariator(economicmodel, 3, 2015)])

    csvvfile.collapse_bang(csvv, qvals.get_seed())

    curr_curvegen = curvegen.CoefficientsCurveGenerator(lambda coeffs: CubicSplineCurve(knots, coeffs),
                                                        ['C'] + ['C^3'] * (len(knots) - 2),
                                                        '100,000 * death/population', csvv)
    farm_curvegen = curvegen.FarmerCurveGenerator(curr_curvegen, covariator, farmer)

    # Collect all baselines
    calculation = Transform(
        YearlyBins('100,000 * death/population', farm_curvegen, "the mortality response curve"),
        '100,000 * death/population', 'deaths/person/year', lambda x: x / 1e5,
        'convert to deaths/person/year', "Divide by 100000 to convert to deaths/person/year.")

    return calculation, [], covariator.get_baseline_args
