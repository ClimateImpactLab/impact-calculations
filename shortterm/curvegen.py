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
        for region, weathers in weatherbundle.baseline_average(maxbaseline): # baseline through maxbaseline
            self.weather_predictors[region] = weathers

        self.econ_predictors = economicmodel.baselined_prepared(maxbaseline, numeconyears, np.mean)

        self.economicmodel = economicmodel

    def get_baseline(self, region):
        return tuple(self.weather_predictors[region] + map(np.log, self.econ_predictors[region]))

if __name__ == '__main__':
    curvegen = FlatCurveGenerator(1234, [1, 1], [[.01, 0], [0, .01]], [0])
    curve = curvegen.get_curve([2])
    print curve(0)

    from impacts.weather import MultivariateHistoricalWeatherBundle
    from adaptation.econmodel import iterate_econmodels

    historicalbundle = MultivariateHistoricalWeatherBundle("/shares/gcp/BCSD/grid2reg/cmip5/historical/CCSM4/{0}/{0}_day_aggregated_historical_r1i1p1_CCSM4_{1}.nc", 1991, 2005, ['pr', 'tas'])
    model, scenario, econmodel = (mse for mse in iterate_econmodels() if mse[0] == 'OECD Env-Growth').next()

    predgen = TemperaturePrecipitationPredictorator(historicalbundle, econmodel, 15, 15, 2005)
    print predgen.get_baseline('CAN.1.2.28')
