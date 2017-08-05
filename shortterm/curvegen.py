import numpy as np
from scipy.stats import multivariate_normal
from openest.generate.curvegen import CurveGenerator
from openest.models.curve import LinearCurve, PolynomialCurve

class CSVVCurveGenerator(CurveGenerator):
    def __init__(self, indepunits, depenunits, covarnames, gamma, residvcv, callback=None):
        super(CSVVCurveGenerator, self).__init__(indepunits, depenunits)

        self.covarnames = covarnames
        assert len(self.covarnames) == len(gamma), "%d <> %d" % (len(covarnames), len(self.gamma))

        self.gamma = gamma
        self.residvcv = residvcv
        self.callback = callback

class LinearCurveGenerator(CSVVCurveGenerator):
    def get_curve(self, region, predictors):
        yy = 0
        for ll in range(len(self.gamma)):
            if self.covarnames[ll] == '1':
                yy += self.gamma[ll]
            else:
                yy += self.gamma[ll] * predictors[self.covarnames[ll]]

        if self.callback is not None:
            self.callback(region, predictors, yy)

        return LinearCurve(yy)

class WeatherPredictorator(object):
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

    def get_current(self, region):
        econpreds = self.econ_predictors.get(region, self.econ_predictors['mean'])
        return {'climtas': self.weather_predictors[region], 'loggdppc': np.log(econpreds['gdppcs']), 'logpopop': np.log(econpreds['popop'])}

if __name__ == '__main__':
    curvegen = LinearCurveGenerator('X', 'Y', 1234, [1, 1], [[.01, 0], [0, .01]], [0])
    curve = curvegen.get_curve([2])
    print curve(0)

    from impacts.weather import HistoricalWeatherBundle
    from adaptation.econmodel import iterate_econmodels

    historicalbundle = HistoricalWeatherBundle("/shares/gcp/BCSD/grid2reg/cmip5/historical/CCSM4/{0}/{0}_day_aggregated_historical_r1i1p1_CCSM4_{1}.nc", 1991, 2005, ['pr', 'tas'], 'historical', 'CCSM4')
    model, scenario, econmodel = (mse for mse in iterate_econmodels() if mse[0] == 'OECD Env-Growth').next()

    predgen = TemperaturePrecipitationPredictorator(historicalbundle, econmodel, 15, 15, 2005)
    print predgen.get_current('CAN.1.2.28')
