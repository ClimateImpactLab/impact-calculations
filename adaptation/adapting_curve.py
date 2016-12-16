import copy
import numpy as np
from openest.models.curve import StepCurve, AdaptableCurve
        
region_stepcurves = {}

class InstantAdaptingStepCurve(AdaptableCurve):
    def __init__(self, beta_generator, get_predictors, bin_limits):
        self.beta_generator = beta_generator
        self.get_predictors = get_predictors
        self.region = None
        self.curr_curve = None
        self.bin_limits = bin_limits

        bin_limits = np.array(bin_limits)
        if bin_limits[0] == -np.inf:
            bin_limits[0] = bin_limits[1] - 10
        if bin_limits[-1] == np.inf:
            bin_limits[-1] = bin_limits[-2] + 10
        self.xx = (bin_limits[1:] + bin_limits[:-1]) / 2

    def create(self, region, predictors):
        copy = self.__class__(self.beta_generator, self.get_predictors, self.bin_limits)
        copy.region = region
        copy.curr_curve = self.beta_generator.get_curve(predictors, None)
        region_stepcurves[region] = copy
        copy.min_beta = np.minimum(0, np.nanmin(np.array(copy.curr_curve.yy)[4:-2]))
        return copy

    def update(self, year, temps):
        predictors = self.get_predictors(self.region, year, temps)
        self.curr_curve = self.beta_generator.get_curve(predictors, self.min_beta)

    def __call__(self, x):
        return self.curr_curve(x)

class ComatoseInstantAdaptingStepCurve(InstantAdaptingStepCurve):
    def __init__(self, beta_generator, get_predictors, bin_limits):
        super(ComatoseInstantAdaptingStepCurve, self).__init__(beta_generator, get_predictors, bin_limits)

    def update(self, year, temps):
        # Ignore for the comatose farmer
        pass

class DumbInstantAdaptingStepCurve(InstantAdaptingStepCurve):
    def __init__(self, beta_generator, get_predictors, bin_limits):
        super(DumbInstantAdaptingStepCurve, self).__init__(beta_generator, get_predictors, bin_limits)

    def update(self, year, temps):
        # Set temps to None so no adaptation to them
        super(DumbInstantAdaptingStepCurve, self).update(year, None)

class AdaptingStepCurve(AdaptableCurve):
    def __init__(self, beta_generator, gamma_generator, get_predictors):
        self.beta_generator = beta_generator
        self.gamma_generator = gamma_generator
        self.get_predictors = get_predictors
        self.region = None
        self.curr_curve = None

    def create(self, region, predictors):
        copy = AdaptingStepCurve(self.beta_generator, self.gamma_generator, self.get_predictors)
        copy.region = region
        copy.curr_curve = self.beta_generator.get_curve(predictors)
        return copy

    def update(self, year, temps):
        predictors = self.get_predictors(region, year, temps)
        final_curve = self.beta_generator.get_curve(predictors)
        gamma_curve = self.gamma_generator.get_curve(predictors)

        yy = []
        for x in self.curr_curve.get_xx():
            gamma = gamma_curve(x)
            if gamma >= 0:
                yy.append(self.curr_curve(x))
            else:
                expgamma = np.exp(gamma)
                newbeta = self.curr_curve(x) * expgamma + final_curve(x) * (1 - expgamma)
                yy.append(newbeta)

        self.curr_curve = StepCurve(self.curr_curve.xxlimits, yy)

    def __call__(self, x):
        return self.curr_curve(x)
