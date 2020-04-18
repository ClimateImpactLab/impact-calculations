from adaptation import csvvfile, curvegen, curvegen_known
from openest.models.curve import ZeroInterceptPolynomialCurve, ClippedCurve, ShiftedCurve, SelectiveInputCurve, CoefficientsCurve
from openest.generate.stdlib import *
from impactcommon.math import minpoly

def prepare_raw(csvv, weatherbundle, economicmodel, qvals, config={}):
    csvvfile.collapse_bang(csvv, qvals.get_seed('csvv'))

    order = len(csvv['gamma'])
    poly_curvegen = curvegen_known.PolynomialCurveGenerator(['C'] + ['C^%d' % pow for pow in range(2, order+1)],
                                                            '100000 * death/population', 'tas', order, csvv)
    curve = poly_curvegen.get_curve('global', 2000, {})

    # Determine minimum value of curve between 10C and 25C
    curvemin = minpoly.findpolymin([0] + curve.ccs, config.get('clip-mintemp', 10), config.get('clip-maxtemp', 25))

    coeff_curve = SelectiveInputCurve(CoefficientsCurve(curve.ccs), list(range(order)))
    shifted_curve = ShiftedCurve(coeff_curve, -curve(curvemin))
    clipped_curve = ClippedCurve(shifted_curve)

    clip_curvegen = curvegen.ConstantCurveGenerator(poly_curvegen.indepunits, poly_curvegen.depenunit, clipped_curve)
    
    # Produce the final calculation
    calculation = Transform(YearlyAverageDay('100000 * death/population', clip_curvegen,
                                             "the mortality response curve"),
                            '100000 * death/population', 'deaths/person/year', lambda x: 365 * x / 1e5,
                            'convert to deaths/person/year', "Divide by 100000 to convert to deaths/person/year.")

    return calculation, []
