"""
Compute minutes lost due to temperature effects
"""

import numpy as np
from openest.generate.stdlib import *
from adaptation import csvvfile

def prepare_csvv(csvvpath, qvals, callback):
    data = csvvfile.read(csvvpath)
    data = csvvfile.collapse_bang(qvals.get_seed())
    
    polyvals = csvvfile.extract_values(data, range(4), r"temp{K}?L0.*")
    tempcurve = curvegen.PolynomialCurveGenerator(4, 'C', 'minutes', None, polyvals['gamma'], polyvals['gammavcv'], polyvals['residvcv'], callback=lambda r, x, y: callback('temp', r, x, y))

    tempeffect = YearlyAverageDay('minutes', tempcurve, 'the quartic temperature effect')

    negtempoffset = curvegen.PolynomialCurveGenerator(4, 'C', 'minutes', None, -polyvals['gamma'], polyvals['gammavcv'], polyvals['residvcv'])
    negtempoffset = YearlyAverageDay('minutes', negtempoffset, 'offset to normalize to 27 degrees', weather_change=lambda temps: np.ones(len(temps)) * 27)

    zerovals = csvvfiles.extract_value(data, 16, "belowzero")
    zerocurve = curvegen.LinearCurveGenerator('is_below', 'minutes', None, zerovals['gamma'], zerovals['gammavcv'], zerovals['residvcv'], callback=lambda r, x, y: callback('zero', r, x, y))
    zeroeffect = YearlyAverageDay('minutes', zerocurve, "effect from days less than 0 C", weather_change=lambda temps: temps < 0)

    return Sum([tempeffect, negtempoffset, zerocurve]), [data['attrs']['version']], data['prednames']
