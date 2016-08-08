"""
Compute conflict risk using reanalyzed data

Temperature is as a z-score ((T_t - mean T) / (sdev T))
Precipitation is as a difference of polynomials (sum_k P^k - mean P^k)
"""

from openest.generate.stdlib import *
from adaptation import csvvfile

def prepare_raw_csvv(csvvpath, pvals):
    data = csvvfile.read(csvvpath)

    tcoeff = LinearInterpolatedValue(extractValues(data, [0]), pvals)
    p3coeffs = LinearInterpolatedPolynomial(extractValues(data, range(1, 4)), pvals)

    teffect = ApplyEstimated(tcoeff, 'z-score', 'delta rate',
        Transform(WeatherVariable('tas'), 'C', 'z-score',
                  lambda tas: (tas - climate_mean('tas')) / climate_sdev('tas'))
    p3effect = ApplyEstimated(p3coeffs, 'anomaly poly', 'delta rate',
        Transform(WeatherVariable('prcp'), 'mm/day', 'anomaly poly',
                  lambda prcp: [prcp - climate_mean('prcp'),
                                prcp**2 - climate_mean('prcp')**2,
                                prcp**3 - climate_mean('prcp')**3])

    return Sum(teffect, p3effect)
