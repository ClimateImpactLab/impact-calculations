from adaptation import csvvfile, curvegen, curvegen_known
from openest.models.curve import ZeroInterceptPolynomialCurve, ClippedCurve, ShiftedCurve, SelectiveInputCurve
from openest.generate.stdlib import *
from impactcommon.math import minspline

knots = [-10, 0, 10, 20, 28, 33]

def prepare_raw(csvv, weatherbundle, economicmodel, qvals):
    csvvfile.collapse_bang(csvv, qvals.get_seed())

    orig_curvegen = curvegen_known.CubicSplineCurveGenerator(['C'] + ['C^3'] * (len(knots) - 2),
                                                              '100000 * death/population', 'spline_variables-',
                                                              knots, csvv)

    curve = orig_curvegen.get_curve('global', 2000, {})
    
    # Determine minimum value of curve between 10C and 25C
    curvemin = minspline.findsplinemin(knots, curve.coeffs, 10, 25)

    shifted_curve = ShiftedCurve(SelectiveInputCurve(curve, [0]), -curve(curvemin))
    clipped_curve = ClippedCurve(shifted_curve)

    clip_curvegen = curvegen.ConstantCurveGenerator(orig_curvegen.indepunits, orig_curvegen.depenunit, clipped_curve)

    # Produce the final calculation
    calculation = Transform(YearlyAverageDay('100000 * death/population', clip_curvegen, "the mortality response curve"),
                            '100000 * death/population', 'deaths/person/year', lambda x: 365 * x / 1e5,
                            'convert to deaths/person/year', "Divide by 100000 to convert to deaths/person/year.")

    return calculation, []
