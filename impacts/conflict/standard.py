"""
Compute conflict risk using reanalyzed data

Temperature is as a z-score ((T_t - mean T) / (sdev T))
"""

import numpy as np
from openest.generate.stdlib import *
from adaptation import csvvfile
from shortterm import curvegen, weather
from climate import forecasts, forecastreader
from openest.models.curve import PolynomialCurve

def prepare_csvv(csvvpath, qvals, callback):
    data = csvvfile.read(csvvpath)
    csvvfile.collapse_bang(data, qvals.get_seed())

    # Load climatology
    tggr = data['gamma'][0:4]
    pggr = data['gamma'][-2:]

    tcurve = curvegen.LinearCurveGenerator('C', 'rate', None, tggr, None, data['residvcv'], callback=lambda r, x, y: callback('temp', r, x, y))

    teffect = SingleWeatherApply('rate', tcurve, 'the linear temperature effect', lambda tp: tp[0])

    p2curve = PolynomialCurve([-np.inf, np.inf], pggr)
    p2effect = SingleWeatherApply('rate', p2curve, 'the quadratic precipitation effect', lambda tp: (365.25 / 30) * (tp[1]**2))

    return Sum([teffect, p2effect]), [data['attrs']['version']], data['prednames']
