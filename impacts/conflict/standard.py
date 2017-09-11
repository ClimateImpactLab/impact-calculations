"""
Compute conflict risk using reanalyzed data

Temperature is as a z-score ((T_t - mean T) / (sdev T))
"""

import numpy as np
from openest.generate.stdlib import *
from adaptation import csvvfile
from shortterm import curvegen, weather
from climate import forecasts, forecastreader
from datastore import irregions
from openest.models.curve import ZeroInterceptPolynomialCurve

def prepare_csvv(csvvpath, qvals, callback, tp_index0):
    data = csvvfile.read(csvvpath)
    csvvfile.collapse_bang(data, qvals.get_seed())

    dependencies = [data['attrs']['version']]
    
    # Load climatology
    prcp_climate_mean = list(forecasts.readncdf_allmonths(forecasts.prcp_climate_path, 'mean'))
    regions = irregions.load_regions("hierarchy.csv", dependencies)

    tggr = data['gamma'][0:4]
    pggr = data['gamma'][-2:]

    tcurve = curvegen.LinearCurveGenerator('C', 'rate', data['covarnames'][0:4], tggr, data['residvcv'], callback=lambda r, x, y: callback('temp', r, x, y))

    teffect = SingleWeatherApply('rate', tcurve, 'the linear temperature effect', lambda tp: tp[tp_index0 + 0])

    p2curve = ZeroInterceptPolynomialCurve([-np.inf, np.inf], pggr)
    p2effect = SingleWeatherApply('rate', p2curve, 'the quadratic precipitation effect', lambda tp: (365.25 / 30) * (tp[to_index0 + 1]**2))

    negp2curve = ZeroInterceptPolynomialCurve([-np.inf, np.inf], -pggr)
    p2climate = MonthlyClimateApply('rate', negp2curve, 'negative climatic precipitation effect', prcp_climate_mean, regions, lambda p: (365.25 / 30) * (p**2))

    return Sum([teffect, p2effect, p2climate]), dependencies, data['covarnames'][0:4]
