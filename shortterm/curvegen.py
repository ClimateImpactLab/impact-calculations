import numpy as np
from scipy.stats import multivariate_normal
from openest.models.curve import FlatCurve

class FlatCurveGenerator(object):
    def __init__(self, seed, gamma, gammavcv, residvcv):
        if seed is None:
            self.gamma = gamma
        else:
            np.random.seed(seed)
            self.gamma = multivariate_normal.rvs(gamma, gammavcv)
        self.residvcv = residvcv

    def get_curve(self, predictors):
        assert len(predictors) == len(self.gamma) - 1

        yy = self.gamma[0] + np.sum(self.gamma[1:] * np.array(predictors))

        return FlatCurve(yy)

if __name__ == '__main__':
    curvegen = FlatCurveGenerator(1234, [1, 1], [[.01, 0], [0, .01]], [0])
    curve = curvegen.get_curve([2])
    print curve(0)
