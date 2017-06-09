import numpy as np
from openest.generate.curvegen import *

region_curves = {}

class CSVVCurveGenerator(CurveGenerator):
    def __init__(self, prednames, indepunits, depenunit, csvv):
        super(CSVVCurveGenerator, self).__init__(indepunits, depenunit)
        self.prednames = prednames

        for ii, predname in enumerate(prednames):
            assert predname in csvv['variables'], "Predictor %s not found in CSVV." % predname
            if predname in csvv['variables']:
                if 'unit' in csvv['variables'][predname]:
                    assert csvv['variables'][predname]['unit'] == indepunits[ii], "Units error for %s: %s <> %s" % (predname, csvv['variables'][predname]['unit'], indepunits[ii])

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

    def get_marginals(self, covar):
        marginals = {} # {predname: sum}
        for predname in set(self.prednames):
            marginals[predname] = self.predgammas[predname][self.predcovars[predname].index(covar)]
        return marginals

    def get_curve(self, region, covariates={}):
        raise NotImplementedError()

class FarmerCurveGenerator(WeatherDelayedCurveGenerator):
    """Handles different adaptation assumptions."""
    def __init__(self, curvegen, covariator, farmer='full', save_curve=True):
        super(FarmerCurveGenerator, self).__init__(curvegen.indepunits, curvegen.depenunit)
        self.curvegen = curvegen
        self.covariator = covariator
        self.farmer = farmer
        self.save_curve = save_curve

    def get_baseline_curve(self, region, *args, **kwargs):
        covariates = self.covariator.get_current(region)
        curve = self.curvegen.get_curve(region, covariates)

        if self.save_curve:
            region_curves[region] = curve

        return curve

    def get_next_curve(self, region, *args, **kwargs):
        if self.farmer == 'full':
            covariates = self.covariator.get_update(region, year, kwargs['weather'])
            curve = self.curvegen.get_curve(region, covariates)
        elif self.farmer == 'coma':
            curve = self.last_curve
        elif self.farmer == 'dumb':
            covariates = self.covariator.get_update(region, year, None)
            curve = self.curvegen.get_curve(region, covariates)
        else:
            raise ValueError("Unknown farmer type " + str(self.farmer))

        if self.save_curve:
            region_curves[region] = curve

        return curve
