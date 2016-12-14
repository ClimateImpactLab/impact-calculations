"""
Compute minutes lost due to temperature effects
"""

import numpy as np
from openest.generate.stdlib import *
from adaptation import csvvfile

def prepare_csvv(csvvpath, qvals, callback):
    data = csvvfile.read(csvvpath)
    data = csvvfile.collapse_bang(qvals.get_seed())

    assert data['prednames'] == ['tempL0', 'temp2L0', 'temp3L0', 'temp4L0', 'tempL0lninc', 'temp2L0lninc', 'temp3L0lninc', 'temp4L0lninc', 'tempL0lnpop', 'temp2L0lnpop', 'temp3L0lnpop', 'temp4L0lnpop', 'tempL0LRTMAX', 'temp2L0LRTMAX', 'temp3L0LRTMAX', 'temp4L0LRTMAX', 'belowzero']
    # Switch to be const, tasmax, loggdppc, logpopop
    oldindices = np.array(0, 3, 1, 2)
    newindices = np.arange(4)
    for kk in range(4):
        csvv['prednames'][kk + newindices * 4] = csvv['prednames'][kk + oldindices * 4]
        csvv['gamma'][kk + newindices * 4] = csvv['gamma'][kk + oldindices * 4]
        csvv['gammavcv'][kk + newindices * 4, :] = csvv['gammavcv'][kk + oldindices * 4, :]
        csvv['gammavcv'][:, kk + newindices * 4] = csvv['gammavcv'][:, kk + oldindices * 4]

    polyvals = csvvfile.extract_values(data, range(4), r"temp{K}?L0.*")
    tempcurve = curvegen.PolynomialCurveGenerator(4, 'C', 'minutes', None, polyvals['gamma'], polyvals['gammavcv'], polyvals['residvcv'], callback=lambda r, x, y: callback('temp', r, x, y))

    tempeffect = YearlyAverageDay('minutes', tempcurve, 'the quartic temperature effect')

    negtempoffset = curvegen.PolynomialCurveGenerator(4, 'C', 'minutes', None, -polyvals['gamma'], polyvals['gammavcv'], polyvals['residvcv'])
    negtempoffset = YearlyAverageDay('minutes', negtempoffset, 'offset to normalize to 27 degrees', weather_change=lambda temps: np.ones(len(temps)) * 27)

    zerovals = csvvfiles.extract_value(data, 16, "belowzero")
    zerocurve = curvegen.LinearCurveGenerator('is_below', 'minutes', None, zerovals['gamma'], zerovals['gammavcv'], zerovals['residvcv'], callback=lambda r, x, y: callback('zero', r, x, y))
    zeroeffect = YearlyAverageDay('minutes', zerocurve, "effect from days less than 0 C", weather_change=lambda temps: temps < 0)

    return Sum([tempeffect, negtempoffset, zerocurve]), [data['attrs']['version']], data['prednames']
