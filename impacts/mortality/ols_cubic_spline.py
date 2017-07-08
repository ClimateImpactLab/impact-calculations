import csv, copy
import numpy as np
from adaptation import csvvfile, curvegen, curvegen_known, covariates, constraints
from generate import caller
from openest.models.curve import ZeroInterceptPolynomialCurve, ClippedCurve, ShiftedCurve, MinimumCurve
from openest.generate.stdlib import *
from openest.generate import diagnostic
from impactcommon.math import minspline

knots = [-10, 0, 10, 20, 28, 33]

def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full'):
    covariator = covariates.CombinedCovariator([covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 30, 2015), {'climtas': 'tas'}),
                                                covariates.EconomicCovariator(economicmodel, 1, 2015)])

    # Don't collapse: already collapsed in allmodels
    #csvvfile.collapse_bang(csvv, qvals.get_seed())

    curr_curvegen = curvegen_known.CubicSplineCurveGenerator(['C'] + ['C^3'] * (len(knots) - 2),
                                                             '100,000 * death/population', 'spline_variables-',
                                                             knots, csvv)

    # Determine minimum value of curve between 10C and 25C
    baselinecurves, baselinemins = constraints.get_curve_minima(weatherbundle, curr_curvegen, covariator, 10, 25,
                                                                lambda curve: minspline.findsplinemin(knots, curve.coeffs, 10, 25))

    def transform(region, curve):
        fulladapt_curve = ShiftedCurve(curve, -curve(baselinemins[region]))
        noincadapt_curve = ShiftedCurve(baselinecurves[region], -baselinecurves[region](baselinemins[region]))

        goodmoney_curve = MinimumCurve(fulladapt_curve, noincadapt_curve)
        return ClippedCurve(goodmoney_curve)

    clip_curvegen = curvegen.TransformCurveGenerator(curr_curvegen, transform)
    farm_curvegen = curvegen.FarmerCurveGenerator(clip_curvegen, covariator, farmer)

    calculation = Transform(YearlyAverageDay('100,000 * death/population', farm_curvegen, "the mortality response curve"),
                            '100,000 * death/population', 'deaths/person/year', lambda x: 365 * x / 1e5,
                            'convert to deaths/person/year', "Divide by 100000 to convert to deaths/person/year.")

    return calculation, [], covariator.get_current
