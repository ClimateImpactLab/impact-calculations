"""
Compute conflict risk using reanalyzed data

Temperature is as a z-score ((T_t - mean T) / (sdev T))
Precipitation is as a difference of polynomials (sum_k P^k - mean P^k)
"""

from openest.generate.stdlib import *
from adaptation import csvvfile
from shortterm import curvegen

def prepare_csvv(csvvpath, qvals):
    data = csvvfile.read(csvvpath)

    ggr = csvvfile.extract_values(data, [0])
    tcoeff = curvegen.FlatCurveGenerator('C', 'rate', qvals.get_seed(), ggr['gamma'], ggr['gammavcv'], ggr['residvcv'])
    #p3coeffs = LinearInterpolatedPolynomial(extract_values(data, range(1, 4)), qvals['precipitation'])

    teffect = InstaZScoreApply('rate', tcoeff, 'the linear temperature effect', 635) #676)

    #teffect = ApplyEstimated(tcoeff, 'z-score', 'delta rate',
    #    RegionalTransform(WeatherVariable('tas'), 'C', 'z-score',
    #                      lambda tas, ii: (tas - climate_mean('tas', ii)) / climate_sdev('tas', ii))
    #p3effect = ApplyEstimated(p3coeffs, 'anomaly poly', 'delta rate',
    #    Transform(WeatherVariable('prcp'), 'mm/day', 'anomaly poly',
    #              lambda prcp: [prcp - climate_mean('prcp'),
    #                            prcp**2 - climate_mean('prcp')**2,
    #                            prcp**3 - climate_mean('prcp')**3])
    #return Sum(teffect, p3effect)

    return teffect, [data['attrs']['version']]
