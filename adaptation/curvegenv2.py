import numpy as np
from openest.models.curve import AdaptableCurve, PolynomialCurve
from openest.generate.curvegen import CurveGenerator

class ConstantCurveGenerator(CurveGenerator):
    def __init__(self, indepunits, depenunits, curve):
        super(ConstantCurveGenerator, self).__init__(indepunits, depenunits)

        self.curve = curve

    def get_curve(self, region, *predictors):
        return curve

class LOrderPolynomialCurveGenerator(CurveGenerator):
    def __init__(self, indepunits, depenunits, order, gamma, predictorator, callback=None):
        super(LOrderPolynomialCurveGenerator, self).__init__(indepunits, depenunits)

        self.order = order
        self.gamma = gamma
        self.predictorator = predictorator
        self.callback = callback

    def get_curve(self, region, *predictors):
        if len(predictors) == 0:
            predictors = self.predictorator.get_baseline(region)

        assert len(predictors) * self.order == len(self.gamma) - self.order, "%d <> %d x %d" % (len(predictors), len(self.gamma), self.order)

        ccs = []
        for oo in range(self.order):
            mygamma = self.gamma[oo + self.order * range(len(predictors) + 1)]
            ccs.append(mygamma[0]  + np.sum(mygamma[1:] * np.array(predictors)))

        if self.callback is not None:
            self.callback(region, predictors, ccs)

        return InstantAdaptingPolynomialCurve(region, ccs, self.predictorator)

class InstantAdaptingPolynomialCurve(AdaptableCurve):
    def __init__(self, region, ccs, predictorator):
        self.region = region
        self.curr_curve = PolynomialCurve([-np.inf, np.inf], ccs)
        self.predictorator = predictorator

    def update(self, year, temps):
        predictors = self.predictorator.get_update(region, year, temps)
        self.curr_curve = self.curvegen.get_curve(self.region).curr_curve

    def __call__(self, x):
        return self.curr_curve(x)
