import csv, copy
import numpy as np
from adaptation import csvvfile, curvegen, curvegen_known, covariates, constraints
from openest.generate.smart_curve import CoefficientsCurve
from openest.models.curve import ZeroInterceptPolynomialCurve, ClippedCurve, ShiftedCurve, MinimumCurve, OtherClippedCurve, SelectiveInputCurve
from openest.generate.stdlib import *
from openest.generate import diagnostic
from impactcommon.math import minpoly

def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full', **kwargs):
    covariator = covariates.CombinedCovariator([covariates.TranslateCovariator(
        covariates.MeanWeatherCovariator(weatherbundle, 30, 2015, 'tas'), {'climtas': 'tas'}),
                                                covariates.EconomicCovariator(economicmodel, 13, 2015),
                                                covariates.HistoricalCovariator(covariates.TranslateCovariator(
                                                    covariates.MeanWeatherCovariator(weatherbundle, 30, 2015, 'tas'), {'climtas': 'tas'}),
                                                                                '.histclim'),
                                                covariates.HistoricalCovariator(covariates.EconomicCovariator(economicmodel, 13, 2015),
                                                                                '.histclim')])

    order = len(csvv['gamma']) / 3
    curr_curvegen = curvegen_known.PolynomialCurveGenerator(['C'] + ['C^%d' % pow for pow in range(2, order+1)],
                                                           '100,000 * death/population', 'tas', order, csvv)
    diff_curvegen = curvegen.DifferenceCurveGenerator(curr_curvegen, curr_curvegen, csvv['prednames'],
                                                      csvv['covarnames'], lambda x: x if len(x) != 4 or x[:3] != 'tas' else x[:-1] + '-poly-' + x[-1],
                                                      lambda x: (x if len(x) != 4 or x[:3] != 'tas' else x[:-1] + '-poly-' + x[-1]) + '.histclim')
    farm_curvegen = curvegen.FarmerCurveGenerator(diff_curvegen, covariator, farmer)

    # Produce the final calculation
    calculation = Transform(LincomDay2Year('100,000 * death/population', farm_curvegen,
                                           "the mortality response curve"),
                            '100,000 * death/population', 'deaths/person/year', lambda x: x / 1e5,
                            'convert to deaths/person/year', "Divide by 100000 to convert to deaths/person/year.")

    return calculation, [], covariator.get_current