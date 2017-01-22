import numpy as np
from openest.generate.curvegen import CurveGenerator

class CSVVCurveGenerator(CurveGenerator):
    def __init__(self, prednames, indepunits, depenunit, csvv):
        super(CSVVCurveGenerator, self).__init__(indepunits, depenunits)
        self.prednames = prednames

        for ii, predname in enumerate(prednames):
            assert csvv['variables'][predname].unit == indepunits[ii]
        assert csvv['variables']['outcome'].unit == depenunit

        # Preprocessing
        self.constant = {} # {predname: constant}
        self.predcovars = {} # {predname: [covarname]}
        self.predgammas = {} # {predname: np.array}
        for predname in set(prednames):
            self.constant[predname] = 0
            self.predcovars[predname] = []
            self.predgammas[predname] = []

            indices = [ii for ii, xx in enumerate(csvv['prednames']) if xx == predname]
            for index in indices:
                if csvv['covarnames'][index] == '1':
                    self.constant[predname] += csvv['gamma'][index]
                else:
                    self.predcovars[predname].append(csvv['covarnames'][index])
                    self.predgammas[predname].append(csvv['gamma'][index])

            self.predgammas[predname] = np.array(self.predgammas[predname])

    def get_coefficients(self, covariates):
        coefficients = {} # {predname: sum}
        for predname in set(self.prednames):
            if len(self.predgammas[predname]) == 0:
                coefficients[predname] = np.nan
            else:
                coefficients[predname] = self.constant[predname] + np.sum(self.predgammas[predname] * np.array([self.covariates[covar] for covar in self.predcovars[predname]]))

        return coefficients

    def get_curve(self, region, covariates={}):
        raise NotImplementedError()

## New-style covariate-based curvegen
class FarmerCurveGenerator(CurveGenerator):
    def __init__(self, indepunits, depenunit, covariator, farmer='full'):
        super(FarmerCurveGenerator, self).__init__(indepunits, depenunit)

        self.covariator = covariator
        self.farmer = farmer

    def get_curve(self, region, covariates={}):
        if len(covariates) == 0:
            covariates = self.covariator.get_baseline(region)

        curr_curvegen = self.curr_curvegen(region, covariates)

        if self.farmer == 'full':
            return InstantAdaptingCurve(region, curr_curve, self.covariator, self.curr_curvegen)
        elif self.farmer == 'coma':
            return ComatoseInstantAdaptingCurve(region, curr_curve, self.covariator, self.curr_curvegen)
        elif self.farmer == 'dumb':
            return DumbInstantAdaptingCurve(region, curr_curve, self.covariator, self.curr_curvegen)
        else:
            raise ValueError("Unknown farmer type " + str(farmer))

from openest.models.curve import AdaptableCurve

class InstantAdaptingCurve(AdaptableCurve):
    def __init__(self, region, curr_curve, covariator, curvegen):
        self.region = region
        self.curr_curve = curr_curve
        self.covariator = covariator
        self.curvegen = curvegen

    def update(self, year, weather):
        covariates = self.covariator.get_update(self.region, year, weather)
        self.curr_curve = self.curvegen.get_curve(self.region, predictors).curr_curve

    def __call__(self, x):
        return self.curr_curve(x)

class ComatoseInstantAdaptingCurve(InstantAdaptingCurve):
    def update(self, year, weather):
        # Ignore for the comatose farmer
        pass

class DumbInstantAdaptingCurve(InstantAdaptingCurve):
    def update(self, year, weather):
        # Set weather to None so no adaptation to it
        super(DumbInstantAdaptingCurve, self).update(year, None)
