"""
Compute conflict risk using reanalyzed data

Temperature is as a z-score ((T_t - mean T) / (sdev T))
"""

import numpy as np
from openest.generate.stdlib import *
from adaptation import csvvfile
from shortterm import curvegen, weather
from climate import forecasts, forecastreader

def prepare_csvv(csvvpath, qvals, callback):
    data = csvvfile.read(csvvpath)
    csvvfile.collapse_bang(data, qvals.get_seed())

    # Load climatology
    tggr = data['gamma'][0:4]
    pggr = data['gamma'][-2:]

    tcurve = curvegen.LinearCurveGenerator('C', 'rate', qvals.get_seed(), tggr, None, tggr['residvcv'], callback=lambda r, x, y: callback('temp', r, x, y))
    qvals.lock() # Use consistent seeds at this point

    teffect = SingleWeatherApply('rate', tcurve, 'the linear temperature effect', lambda tp: tp[0])

    pggr = csvvfile.extract_values(data, range(1, 4))
    p3curve = curvegen.PolynomialCurveGenerator(3, 'mm/month', 'rate', qvals.get_seed(1), pggr, None, pggr['residvcv'], callback=lambda r, x, y: callback('prcp', r, x, y))
    p3effect = SingleWeatherApply('rate', p3curve, 'the quadratic precipitation effect', lambda tp: (365.25 / 30) * (tp[1]**2))

    return Sum([teffect, p3effect]), [data['attrs']['version']], data['prednames']
