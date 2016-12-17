import numpy as np
from openest.models.curve import AdaptableCurve, PolynomialCurve
from openest.generate.curvegen import CurveGenerator

class ConstantCurveGenerator(CurveGenerator):
    def __init__(self, indepunits, depenunits, curve):
        super(ConstantCurveGenerator, self).__init__(indepunits, depenunits)

        self.curve = curve

    def get_curve(self, region, *predictors):
        return self.curve

region_polycurves = {}

class LOrderPolynomialCurveGenerator(CurveGenerator):
    def __init__(self, indepunits, depenunits, order, gamma, predictorator, covariates, callback=None, farmer='full'):
        super(LOrderPolynomialCurveGenerator, self).__init__(indepunits, depenunits)

        self.order = order
        self.gamma = gamma
        self.predictorator = predictorator
        self.covariates = covariates
        self.callback = callback
        self.farmer = farmer

        assert len(self.covariates) * self.order == len(self.gamma) - self.order, "%d x %d <> %d - %d" % (len(self.covariates), self.order, len(self.gamma), self.order)

    def get_curve(self, region, predictors={}):
        if len(predictors) == 0:
            predictors = self.predictorator.get_baseline(region)
        covarvals = np.array([predictors[covar] for covar in self.covariates])

        ccs = []
        for oo in range(self.order):
            mygamma = self.gamma[oo + self.order * np.arange(len(self.covariates) + 1)]
            ccs.append(mygamma[0]  + np.sum(mygamma[1:] * covarvals))

        if self.callback is not None:
            self.callback(region, predictors, ccs)

        if self.farmer == 'full':
            curve = InstantAdaptingPolynomialCurve(region, ccs, self.predictorator, self)
        elif self.farmer == 'coma':
            curve = ComatoseInstantAdaptingPolynomialCurve(region, ccs, self.predictorator, self)
        elif self.farmer == 'dumb':
            curve = DumbInstantAdaptingPolynomialCurve(region, ccs, self.predictorator, self)
            
        region_polycurves[region] = curve

        return curve

class InstantAdaptingPolynomialCurve(AdaptableCurve):
    def __init__(self, region, ccs, predictorator, curvegen):
        self.region = region
        self.curr_curve = PolynomialCurve([-np.inf, np.inf], ccs)
        self.predictorator = predictorator
        self.curvegen = curvegen

    def update(self, year, temps):
        predictors = self.predictorator.get_update(self.region, year, temps)
        self.curr_curve = self.curvegen.get_curve(self.region, predictors).curr_curve

    def __call__(self, x):
        return self.curr_curve(x)

class ComatoseInstantAdaptingPolynomialCurve(InstantAdaptingPolynomialCurve):
    def update(self, year, temps):
        # Ignore for the comatose farmer
        pass

class DumbInstantAdaptingPolynomialCurve(InstantAdaptingPolynomialCurve):
    def update(self, year, temps):
        # Set temps to None so no adaptation to them
        super(DumbInstantAdaptingPolynomialCurve, self).update(year, None)
