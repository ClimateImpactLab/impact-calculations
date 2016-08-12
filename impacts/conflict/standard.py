"""
Compute conflict risk using reanalyzed data

Temperature is as a z-score ((T_t - mean T) / (sdev T))
Precipitation is as a difference of polynomials (sum_k P^k - mean P^k)
"""

import numpy as np
from openest.generate.stdlib import *
from adaptation import csvvfile
from shortterm import curvegen

def prepare_csvv(csvvpath, qvals):
    data = csvvfile.read(csvvpath)

    tggr = csvvfile.extract_values(data, [0])
    tcurve = curvegen.FlatCurveGenerator('C', 'rate', qvals.get_seed(), tggr['gamma'], tggr['gammavcv'], tggr['residvcv'])
    pggr = csvvfile.extract_values(data, range(1, 4))
    p3curve = curvegen.PolynomialCurveGenerator(3, 'sqrt mm/day', 'rate', qvals.get_seed() + 1, tggr['gamma'], tggr['gammavcv'], tggr['residvcv'])

    teffect = InstaZScoreApply('rate', tcurve, 'the linear temperature effect', 676)
    p3effect = SingleWeatherApply('rate', p3curve, 'the cubic precipitation effect', 676, np.sqrt)

    return Sum([teffect, p3effect]), [data['attrs']['version']]
