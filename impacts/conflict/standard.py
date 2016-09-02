"""
Compute conflict risk using reanalyzed data

Temperature is as a z-score ((T_t - mean T) / (sdev T))
Precipitation is as a difference of polynomials (sum_k P^k - mean P^k)
"""

import numpy as np
from openest.generate.stdlib import *
from adaptation import csvvfile
from shortterm import curvegen, weather
from climate import forecasts, forecastreader

def prepare_csvv(csvvpath, qvals, callback):
    data = csvvfile.read(csvvpath)

    # Load climatology
    prcp_climate_mean = list(forecasts.readncdf_allpred(forecasts.prcp_climate_path, 'mean', 0))
    regions = weather.ForecastBundle(forecastreader.MonthlyForecastReader(forecasts.prcp_climate_path, 'mean')).regions

    tggr = csvvfile.extract_values(data, [0])
    tcurve = curvegen.LinearCurveGenerator('C', 'rate', qvals.get_seed(), tggr['gamma'], tggr['gammavcv'], tggr['residvcv'], callback=lambda r, x, y: callback('temp', r, x, y))
    qvals.lock() # Use consistent seeds at this point

    teffect = SingleWeatherApply('rate', tcurve, 'the linear temperature effect', lambda tp: tp[0])

    if '_tavg_' in csvvpath or 'interpersonal_violent' in csvvpath:
        return teffect, [data['attrs']['version']], data['prednames']

    pggr = csvvfile.extract_values(data, range(1, 4))
    p3curve = curvegen.PolynomialCurveGenerator(3, 'mm/month', 'rate', qvals.get_seed(1), pggr['gamma'], pggr['gammavcv'], pggr['residvcv'], callback=lambda r, x, y: callback('prcp', r, x, y))
    p3effect = SingleWeatherApply('rate', p3curve, 'the cubic precipitation effect', lambda tp: (365.25 / 30) * (tp[1]**2))
    negp3curve = curvegen.PolynomialCurveGenerator(3, 'mm/month', 'rate', qvals.get_seed(1), -pggr['gamma'], pggr['gammavcv'], pggr['residvcv'])
    p3climate = MonthlyClimateApply('rate', negp3curve, 'negative climatic precipitation effect', prcp_climate_mean, regions, lambda p: (365.25 / 30) * (p**2))

    return Sum([teffect, p3effect, p3climate]), [data['attrs']['version']], data['prednames']
