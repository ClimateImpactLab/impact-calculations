import numpy as np
from openest.generate import smart_curve, curvegen

def interpret(name, models, extras):
    if name in models:
        return models[name], extras[name]

    if ' * ' in name:
        chunks = name.split(' * ', 1)
        curve_left, extras_left = interpret(chunks[0], models, extras)
        curve_right, extras_right = interpret(chunks[1], models, extras)

        extras = {}
        extras.update(extras_left)
        extras.update(extras_right)

        if isinstance(curve_left, curvegen.CurveGenerator) and isinstance(curve_right, curvegen.CurveGenerator):
            curve = curvegen.TransformCurveGenerator(lambda region, curve1, curve2: smart_curve.ProductCurve(curve_left, curve_right), "Curve product", curve_left, curve_right)
        elif isinstance(curve_left, curvegen.CurveGenerator):
            curve = curvegen.TransformCurveGenerator(lambda region, curve1: smart_curve.ProductCurve(curve1, curve_right), "Curve product", curve_left)
        elif isinstance(curve_right, curvegen.CurveGenerator):
            curve = curvegen.TransformCurveGenerator(lambda region, curve2: smart_curve.ProductCurve(curve_left, curve2), "Curve product", curve_right)
        else:
            curve = smart_curve.ProductCurve(curve_left, curve_right)
            
        return curve, extras

    evalglobals = {'step': lambda variable, value, levels: (smart_curve.StepCurve([-np.inf, value, np.inf], levels, variable), {})}

    curve, extras = eval(name, evalglobals)
    assert isinstance(curve, smart_curve.SmartCurve)
    return curve, extras
