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

def prepare_csvv(csvvpath, qvals, callback, adm0level):
    data = csvvfile.read(csvvpath)
    csvvfile.collapse_bang(data, qvals.get_seed())

    dependencies = [data['attrs']['version']]

    # Load climatology
    prcp_climate_mean = forecasts.readncdf_allmonths(forecasts.prcp_mean_climate_path, 'prcp')
    regions = irregions.load_regions("hierarchy.csv", dependencies)

    if adm0level:
        tp_index0 = 0
        # Replace precip with mean-by-country
        bycountry = forecasts.get_means(regions, lambda ii: prcp_climate_mean[:, ii])
        
        for ii in range(len(regions)):
            prcp_climate_mean[:, ii] = bycountry[regions[ii][:3]]
    else:
        tp_index0 = 2

        # Replace precip with mean-by-country
        bycountry = forecasts.get_means(regions, lambda ii: prcp_climate_mean[:, ii])
        
        for ii in range(len(regions)):
            prcp_climate_mean[:, ii] -= bycountry[regions[ii][:3]]

    tggr = data['gamma'][0:4]
    pggr = data['gamma'][-2:]

    tcurve = curvegen.LinearCurveGenerator('C', 'rate', data['covarnames'][0:4], tggr, data['residvcv'], callback=lambda r, x, y: callback('temp', r, x, y))

    teffect = SingleWeatherApply('rate', tcurve, 'the linear temperature effect', lambda tp: tp[tp_index0 + 0])

    mmday2cmyear = 365.25 / 10 # 1 mm / day * 365.25 day / year * 1 cm / 10 mm
    
    p2curve = ZeroInterceptPolynomialCurve([-np.inf, np.inf], pggr)
    p2effect = SingleWeatherApply('rate', p2curve, 'the quadratic precipitation effect', lambda tp: mmday2cmyear * tp[tp_index0 + 1])

    negp2curve = ZeroInterceptPolynomialCurve([-np.inf, np.inf], -pggr)
    p2climate = MonthlyClimateApply('rate', negp2curve, 'negative climatic precipitation effect', prcp_climate_mean, regions, lambda p: mmday2cmyear * p)

    return Sum([teffect, p2effect, p2climate]), dependencies, data['covarnames'][0:4]
