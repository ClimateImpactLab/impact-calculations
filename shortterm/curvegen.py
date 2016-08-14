import numpy as np
from scipy.stats import multivariate_normal
from openest.generate.curvegen import CurveGenerator
from openest.models.curve import FlatCurve, PolynomialCurve

class CSVVCurveGenerator(CurveGenerator):
    def __init__(self, indepunits, depenunits, seed, gamma, gammavcv, residvcv, callback=None):
        super(CSVVCurveGenerator, self).__init__(indepunits, depenunits)

        if seed is None:
            self.gamma = gamma
        else:
            np.random.seed(seed)
            self.gamma = multivariate_normal.rvs(gamma, gammavcv)
        self.residvcv = residvcv

        self.callback = callback

class FlatCurveGenerator(CSVVCurveGenerator):
    def get_curve(self, region, *predictors):
        assert len(predictors) == len(self.gamma) - 1, "%d <> %d" % (len(predictors), len(self.gamma) - 1)

        yy = self.gamma[0] + np.sum(self.gamma[1:] * np.array(predictors))

        if self.callback is not None:
            self.callback(region, predictors, yy)

        return FlatCurve(yy)

class PolynomialCurveGenerator(CSVVCurveGenerator):
    def __init__(self, order, indepunits, depenunits, seed, gamma, gammavcv, residvcv, callback=None):
        super(PolynomialCurveGenerator, self).__init__(indepunits, depenunits, seed, gamma, gammavcv, residvcv)
        self.order = order
        self.callback = callback

    def get_curve(self, region, *predictors):
        assert len(predictors) * self.order == len(self.gamma) - self.order, "%d <> %d x %d" % (len(predictors), len(self.gamma), self.order)

        ccs = []
        for oo in range(self.order):
            mygamma = self.gamma[oo * (len(predictors) + 1):(oo + 1) * (len(predictors) + 1)]
            ccs.append(mygamma[0]  + np.sum(mygamma[1:] * np.array(predictors)))

        if self.callback is not None:
            self.callback(region, predictors, ccs)

        return PolynomialCurve([-np.inf, np.inf], ccs)

class TemperaturePrecipitationPredictorator(object):
    def __init__(self, weatherbundle, economicmodel, numtempyears, numeconyears, maxbaseline, polyorder=1):
        self.numtempyears = numtempyears
        self.numeconyears = numeconyears
        self.polyorder = polyorder

        print "Collecting baseline information..."
        self.weather_predictors = {}
        for region, weathers in weatherbundle.baseline_average(maxbaseline): # baseline through maxbaseline
            self.weather_predictors[region] = weathers

        self.econ_predictors = economicmodel.baseline_prepared(maxbaseline, numeconyears, np.mean)

        self.economicmodel = economicmodel

    def get_baseline(self, region):
        if self.polyorder == 1:
            return tuple(self.weather_predictors[region] + map(np.log, self.econ_predictors.get(region, self.econ_predictors['mean'])))
        else:
            preds = np.array(self.weather_predictors[region] + map(np.log, self.econ_predictors.get(region, self.econ_predictors['mean'])))
            allpreds = []
            for order in range(self.polyorder):
                allpreds.extend(preds ** (order + 1))
            return tuple(allpreds)

if __name__ == '__main__':
    curvegen = FlatCurveGenerator('X', 'Y', 1234, [1, 1], [[.01, 0], [0, .01]], [0])
    curve = curvegen.get_curve([2])
    print curve(0)

    from impacts.weather import MultivariateHistoricalWeatherBundle
    from adaptation.econmodel import iterate_econmodels

    historicalbundle = MultivariateHistoricalWeatherBundle("/shares/gcp/BCSD/grid2reg/cmip5/historical/CCSM4/{0}/{0}_day_aggregated_historical_r1i1p1_CCSM4_{1}.nc", 1991, 2005, ['pr', 'tas'])
    model, scenario, econmodel = (mse for mse in iterate_econmodels() if mse[0] == 'OECD Env-Growth').next()

    predgen = TemperaturePrecipitationPredictorator(historicalbundle, econmodel, 15, 15, 2005)
    print predgen.get_baseline('CAN.1.2.28')
