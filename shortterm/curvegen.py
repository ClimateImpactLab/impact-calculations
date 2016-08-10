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

class TemperaturePrecipitationPredictorator(object):
    def __init__(self, weatherbundle, economicmodel, numtempyears, numeconyears, maxbaseline):
        self.numtempyears = numtempyears
        self.numeconyears = numeconyears

        print "Collecting baseline information..."
        self.weather_predictors = {}
        for region, weathers in weatherbundle.baseline_values(maxbaseline): # baseline through maxbaseline
            self.weather_predictors[region] = [weather[-numtempyears:] for weather in weathers]

        gdppc_predictors = {}
        allmeans = []
        for region, gdppcs, density in economicmodel.baseline_values(maxbaseline): # baseline through maxbaseline
            allmeans.append(np.mean(gdppcs[-numeconyears:]))
            gdppc_predictors[region] = gdppcs[-numeconyears:]

        gdppc_predictors['mean'] = np.mean(allmeans)

        self.gdppc_predictors = gdppc_predictors

        self.economicmodel = economicmodel

    def get_baseline(self, region):
        gdppcs = self.gdppc_predictors.get(region, None)
        if gdppcs is None:
            gdppcs = self.gdppc_predictors['mean']
        return ((np.mean(self.temp_predictors[region]), np.mean(gdppcs)),)

if __name__ == '__main__':
    curvegen = FlatCurveGenerator(1234, [1, 1], [[.01, 0], [0, .01]], [0])
    curve = curvegen.get_curve([2])
    print curve(0)
