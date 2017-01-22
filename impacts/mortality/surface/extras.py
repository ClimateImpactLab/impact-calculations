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
