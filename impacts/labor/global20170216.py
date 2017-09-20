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

def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full', config={}):
    reader_coldd = discover.discover_yearly_corresponding(files.sharedpath('climate/BCSD/aggregation/cmip5_new/IR_level'),
                                                          weatherbundle.scenario, 'Degreedays_tasmax',
                                                          weatherbundle.model, 'coldd_agg')
    reader_hotdd = discover.discover_yearly_corresponding(files.sharedpath('climate/BCSD/aggregation/cmip5_new/IR_level'),
                                                          weatherbundle.scenario, 'Degreedays_tasmax',
                                                          weatherbundle.model, 'hotdd_agg')

    predgen = covariates.CombinedCovariator([covariates.YearlyWeatherCovariator(reader_coldd, weatherbundle.regions, 2015,
                                                                                weatherbundle.is_historical(), config=config.get('climcovar', {})),
                                             covariates.YearlyWeatherCovariator(reader_hotdd, weatherbundle.regions, 2015,
                                                                                weatherbundle.is_historical(), config=config.get('climcovar', {})),
                                             covariates.EconomicCovariator(economicmodel, 2015, config=config.get('econcovar', {}))])
    predgen2 = covariates.CombinedCovariator([covariates.YearlyWeatherCovariator(reader_coldd, weatherbundle.regions, 2015,
                                                                                 weatherbundle.is_historical(), config=config.get('climcovar', {})),
                                              covariates.YearlyWeatherCovariator(reader_hotdd, weatherbundle.regions, 2015,
                                                                                 weatherbundle.is_historical(), config=config.get('climcovar', {})),
                                              covariates.EconomicCovariator(economicmodel, 2015, config=config.get('econcovar', {}))])

    csvvfile.collapse_bang(csvv, qvals.get_seed())

    subcsvv = csvvfile.subset(csvv, ['tasmax', 'tasmax2', 'tasmax3', 'tasmax4'])

    temp_curvegen = curvegen_known.PolynomialCurveGenerator('C', 'minutes worked by individual', 'tasmax', 4, subcsvv)
    farm_temp_curvegen = curvegen.FarmerCurveGenerator(temp_curvegen, predgen, farmer)
    tempeffect = YearlyDividedPolynomialAverageDay('minutes worked by individual', farm_temp_curvegen, 'the quartic temperature effect')

    negsubcsvv = copy.copy(subcsvv)
    negsubcsvv['gamma'] = -negsubcsvv['gamma']

    negtempoffset_curvegen = curvegen_known.PolynomialCurveGenerator('C', 'minutes worked by individual', 'tasmax', 4, negsubcsvv)
    farm_negtempoffset_curvegen = curvegen.FarmerCurveGenerator(negtempoffset_curvegen, predgen2, farmer=farmer, save_curve=False)
    negtempeffect = YearlyAverageDay('minutes worked by individual', farm_negtempoffset_curvegen, 'offset to normalize to 27 degrees', weather_change=lambda temps: np.ones(len(temps)) * 27)

    zerocurvegen = ConstantCurveGenerator('C', 'minutes worked by individual', FlatCurve(csvv['gamma'][-1]))
    zeroeffect = YearlyAverageDay('minutes worked by individual', zerocurvegen, "effect from days less than 0 C", weather_change=lambda temps: temps[:, 0] < 0)

    calculation = Sum([tempeffect, negtempeffect, zeroeffect])

    return calculation, [], predgen.get_current
