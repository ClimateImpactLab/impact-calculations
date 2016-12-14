from openest.generate.curvegen import CurveGenerator

class ConstantCurveGenerator(CurveGenerator):
    def __init__(self, indepunits, depenunits, curve):
        super(ConstantCurveGenerator, self).__init__(indepunits, depenunits)

        self.curve = curve

    def get_curve(self, region, *predictors):
        return curve

class LOrderPolynomialCurveGenerator(CurveGenerator):
    def __init__(self, indepunits, depenunits, order, gamma, callback=None):
        super(LOrderPolynomialCurveGenerator, self).__init__(indepunits, depenunits)

        self.order = order
        self.gamma = gamma
        self.callback = callback

    def get_curve(self, region, *predictors):
        assert len(predictors) * self.order == len(self.gamma) - self.order, "%d <> %d x %d" % (len(predictors), len(self.gamma), self.order)

        ccs = []
        for oo in range(self.order):
            mygamma = self.gamma[oo + self.order * range(len(predictors) + 1)]
            ccs.append(mygamma[0]  + np.sum(mygamma[1:] * np.array(predictors)))

        if self.callback is not None:
            self.callback(region, predictors, ccs)

        return PolynomialCurve([-np.inf, np.inf], ccs)
