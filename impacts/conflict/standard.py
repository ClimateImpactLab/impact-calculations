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
    prcp_climate_mean = list(forecasts.readncdf_allpred(forecasts.prcp_climate_path, 'mean', 0))
    regions = weather.ForecastBundle(forecastreader.MonthlyForecastReader(forecasts.prcp_climate_path, 'mean')).regions

    tggr = data['gamma'][0:4]
    pggr = data['gamma'][-2:]

    tcurve = curvegen.LinearCurveGenerator('C', 'rate', data['covarnames'][0:4], tggr, data['residvcv'], callback=lambda r, x, y: callback('temp', r, x, y))

    teffect = SingleWeatherApply('rate', tcurve, 'the linear temperature effect', lambda tp: tp[0, 0])

    p2curve = PolynomialCurve([-np.inf, np.inf], pggr)
    p2effect = SingleWeatherApply('rate', p2curve, 'the quadratic precipitation effect', lambda tp: (365.25 / 30) * (tp[0, 1]**2))

    negp2curve = PolynomialCurve([-np.inf, np.inf], -pggr)
    print negp2curve(68.35459792023)
    p2climate = MonthlyClimateApply('rate', negp2curve, 'negative climatic precipitation effect', prcp_climate_mean, regions, lambda p: (365.25 / 30) * (p**2))

    return Sum([teffect, p2effect, p2climate]), [data['attrs']['version']], data['covarnames'][0:4]
