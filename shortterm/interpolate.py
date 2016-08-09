class InterpolatedLinearCurve(InterpolatableCurve):
    def __init__(self, qval, gamma, gammavcv, residvcv):
        self.gamma = multivariate_normal(gamma, gammavcv)
        self.residvcv = residvcv
