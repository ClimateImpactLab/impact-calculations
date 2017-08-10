"""
Compute minutes lost due to temperature effects
"""

import copy
import numpy as np
from openest.generate.stdlib import *
from openest.models.curve import FlatCurve
from openest.generate.curvegen import ConstantCurveGenerator
from adaptation import csvvfile, covariates, curvegen_known, curvegen
from climate import discover
from impactlab_tools.utils import files

def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full', clipping=True):
    reader_coldd = discover.discover_yearly_corresponding(files.sharedpath('climate/BCSD/aggregation/cmip5_new/IR_level'),
                                                          weatherbundle.scenario, 'Degreedays_tasmax',
                                                          weatherbundle.model, 'coldd_agg')
    reader_hotdd = discover.discover_yearly_corresponding(files.sharedpath('climate/BCSD/aggregation/cmip5_new/IR_level'),
                                                          weatherbundle.scenario, 'Degreedays_tasmax',
                                                          weatherbundle.model, 'hotdd_agg')

    predgen = covariates.CombinedCovariator([covariates.YearlyWeatherCovariator(reader_coldd, weatherbundle.regions, 2015, 15,
                                                                                weatherbundle.is_historical()),
                                             covariates.YearlyWeatherCovariator(reader_hotdd, weatherbundle.regions, 2015, 15,
                                                                                weatherbundle.is_historical()),
                                             covariates.EconomicCovariator(economicmodel, 1, 2015)])

    csvvfile.collapse_bang(csvv, qvals.get_seed())

    order = len(set(csvv['prednames'])) - 1 # -1 because of belowzero
    subcsvv = csvvfile.subset(csvv, ['tasmax'] + ['tasmax%d' % power for power in range(2, order + 1)])

    lt27_curvegen = curvegen_known.PolynomialCurveGenerator('C', 'minutes worked by individual', 'tasmax', 4, csvvfile.drop_covariates(subcsvv, 'hotdd_agg'))
    gt27_curvegen = curvegen_known.PolynomialCurveGenerator('C', 'minutes worked by individual', 'tasmax', 4, csvvfile.drop_covariates(subcsvv, 'coldd_agg'))
    piece_curvegen = curvegen.TransformCurveGenerator(make_piecewise, lt27_curvegen, gt27_curvegen)
    shift_curven = curvegen.TransformCurveGenerator(shift_piecewise, piece_curvegen, clipping=clipping) # both clip and subtract curve at 27

    farm_temp_curvegen = curvegen.FarmerCurveGenerator(piece_curvegen, predgen, farmer)
    tempeffect = YearlyDividedPolynomialAverageDay('minutes worked by individual', farm_temp_curvegen, 'the temperature effect')

    zerocurvegen = ConstantCurveGenerator('C', 'minutes worked by individual', FlatCurve(csvv['gamma'][-1]))
    zeroeffect = YearlyAverageDay('minutes worked by individual', zerocurvegen, "effect from days less than 0 C", weather_change=lambda temps: temps[:, 0] < 0)

    calculation = Sum([tempeffect, zeroeffect])

    return calculation, [], predgen.get_current
