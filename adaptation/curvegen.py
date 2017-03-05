import numpy as np
from openest.generate.curvegen import CurveGenerator
from openest.models.curve import AdaptableCurve

region_curves = {}

class CSVVCurveGenerator(CurveGenerator):
    def __init__(self, prednames, indepunits, depenunit, csvv):
        super(CSVVCurveGenerator, self).__init__(indepunits, depenunit)
        self.prednames = prednames

        for ii, predname in enumerate(prednames):
            assert predname in csvv['variables'], "Predictor %s not found in CSVV." % predname
            if predname in csvv['variables']:
                assert 'unit' in csvv['variables'][predname], "Predictor %s does not have units." % predname
                assert csvv['variables'][predname]['unit'] == indepunits[ii]

        assert csvv['variables']['outcome']['unit'] == depenunit, "Dependent units %s does not match %s." % (csvv['variables']['outcome']['unit'], depenunit)

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

    def get_coefficients(self, covariates, debug=False):
        coefficients = {} # {predname: sum}
        for predname in set(self.prednames):
            if len(self.predgammas[predname]) == 0:
                coefficients[predname] = np.nan
            else:
                try:
                    coefficients[predname] = self.constant[predname] + np.sum(self.predgammas[predname] * np.array([covariates[covar] for covar in self.predcovars[predname]]))
                except Exception as e:
                    print "Available covariates:"
                    print covariates
                    raise e

        return coefficients

    def get_curve(self, region, covariates={}):
        raise NotImplementedError()

## New-style covariate-based curvegen
class FarmerCurveGenerator(CurveGenerator):
    def __init__(self, curr_curvegen, covariator, farmer='full', save_curve=True):
        super(FarmerCurveGenerator, self).__init__(curr_curvegen.indepunits, curr_curvegen.depenunit)
        self.curr_curvegen = curr_curvegen
        self.covariator = covariator
        self.farmer = farmer
        self.save_curve = save_curve

    def get_curve(self, region, covariates={}):
        if len(covariates) == 0:
            covariates = self.covariator.get_baseline(region)

        curr_curve = self.curr_curvegen.get_curve(region, covariates)

        if self.farmer == 'full':
            full_curve = InstantAdaptingCurve(region, curr_curve, self.covariator, self.curr_curvegen)
        elif self.farmer == 'coma':
            full_curve = ComatoseInstantAdaptingCurve(region, curr_curve, self.covariator, self.curr_curvegen)
        elif self.farmer == 'dumb':
            full_curve = DumbInstantAdaptingCurve(region, curr_curve, self.covariator, self.curr_curvegen)
        else:
            raise ValueError("Unknown farmer type " + str(self.farmer))

        if self.save_curve:
            region_curves[region] = full_curve

        return full_curve

class InstantAdaptingCurve(AdaptableCurve):
    def __init__(self, region, curr_curve, covariator, curvegen):
        super(InstantAdaptingCurve, self).__init__(curr_curve.xx)

        self.region = region
        self.curr_curve = curr_curve
        self.covariator = covariator
        self.curvegen = curvegen

    def update(self, year, weather):
        covariates = self.covariator.get_update(self.region, year, weather)
        self.curr_curve = self.curvegen.get_curve(self.region, covariates)

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
