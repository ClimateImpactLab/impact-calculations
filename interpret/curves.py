from openest.generate import smart_curve

def interpret(name, models, extras):
    if name in models:
        return models[name], extras[name]

    if ' * ' in name:
        chunks = name.split(' * ', 1)
        curve_left, extras_left = interpret(chunks[0], models)
        curve_right, extras_right = interpret(chunks[1], models)

        extras = {}
        extras.update(extras_left)
        extras.update(extras_right)

        return smart_curve.ProductCurve(curve_left, curve_right), extras

    evalglobals = {'step': lambda value, levels: (smart_curve.StepCurve([-np.inf, value, np.inf], levels), {})}

    curve, extras = eval(name, evalglobals)
    assert isinstance(curve, smart_curve.SmartCurve)
    return curve, extras
