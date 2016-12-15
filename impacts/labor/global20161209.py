"""
Compute minutes lost due to temperature effects
"""

import numpy as np
from openest.generate.stdlib import *
from openest.models.curve import FlatCurve
from adaptation import csvvfile
from adaptation.curvegenv2 import ConstantCurveGenerator, LOrderPolynomialCurveGenerator
from adaptation.adapting_curve import TemperatureIncomeDensityPredictorator

def prepare_interp_raw2(csvv, weatherbundle, economicmodel, qvals, callback):
    predgen = TemperatureIncomeDensityPredictorator(weatherbundle, economicmodel, 15, 3, 2015)

    csvvfile.collapse_bang(csvv, qvals.get_seed())

    assert csvv['prednames'] == ['tempL0', 'temp2L0', 'temp3L0', 'temp4L0', 'tempL0lninc', 'temp2L0lninc', 'temp3L0lninc', 'temp4L0lninc', 'tempL0lnpop', 'temp2L0lnpop', 'temp3L0lnpop', 'temp4L0lnpop', 'tempL0LRTMAX', 'temp2L0LRTMAX', 'temp3L0LRTMAX', 'temp4L0LRTMAX', 'belowzero']
    # Switch to be const, tasmax, loggdppc, logpopop
    oldindices = np.array([0, 3, 1, 2])
    newindices = np.arange(4)
    for kk in range(4):
        ##csvv['prednames'][kk + newindices * 4] = csvv['prednames'][kk + oldindices * 4] # python makes tough
        csvv['gamma'][kk + newindices * 4] = csvv['gamma'][kk + oldindices * 4]
        # VCV is already collapsed
        #csvv['gammavcv'][kk + newindices * 4, :] = csvv['gammavcv'][kk + oldindices * 4, :]
        #csvv['gammavcv'][:, kk + newindices * 4] = csvv['gammavcv'][:, kk + oldindices * 4]

    polyvals = csvv['gamma'][:-1]
    tempcurvegen = LOrderPolynomialCurveGenerator('C', 'minutes', 4, polyvals, predgen, callback=lambda r, x, y: callback('temp', r, x, y))
    tempeffect = YearlyAverageDay('minutes', tempcurvegen, 'the quartic temperature effect')

    negtempoffsetgen = LOrderPolynomialCurveGenerator('C', 'minutes', 4, -polyvals, predgen)
    negtempeffect = YearlyAverageDay('minutes', negtempoffsetgen, 'offset to normalize to 27 degrees', weather_change=lambda temps: np.ones(len(temps)) * 27)

    zerocurvegen = ConstantCurveGenerator('C', 'minutes', FlatCurve(csvv['gamma'][-1]))
    zeroeffect = YearlyAverageDay('minutes', zerocurvegen, "effect from days less than 0 C", weather_change=lambda temps: temps < 0)

    calculation = Sum([tempeffect, negtempeffect, zeroeffect])

    return calculation, []
