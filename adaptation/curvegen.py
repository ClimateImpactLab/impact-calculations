import numpy as np
from openest.generate.curvegen import *
from openest.generate import checks

region_curves = {}

class CSVVCurveGenerator(CurveGenerator):
    def __init__(self, prednames, indepunits, depenunit, csvv):
        super(CSVVCurveGenerator, self).__init__(indepunits, depenunit)
        self.prednames = prednames
        self.csvv = csvv

        for ii, predname in enumerate(prednames):
            if predname not in csvv['variables']:
                print "WARNING: Predictor %s definition not found in CSVV." % predname
            else:
                if 'unit' in csvv['variables'][predname]:
                    assert checks.loosematch(csvv['variables'][predname]['unit'], indepunits[ii]), "Units error for %s: %s <> %s" % (predname, csvv['variables'][predname]['unit'], indepunits[ii])

        if 'outcome' not in csvv['variables']:
            print "WARNING: Dependent variable definition not in CSVV."
        else:
            assert checks.loosematch(csvv['variables']['outcome']['unit'], depenunit), "Dependent units %s does not match %s." % (csvv['variables']['outcome']['unit'], depenunit)

        # Preprocessing
        self.constant = {} # {predname: constant}
        self.predcovars = {} # {predname: [covarname]}
        self.predgammas = {} # {predname: np.array}
        for predname in set(prednames):
            self.constant[predname] = np.nan
            self.predcovars[predname] = []
            self.predgammas[predname] = []

            indices = [ii for ii, xx in enumerate(csvv['prednames']) if xx == predname]
            for index in indices:
                if csvv['covarnames'][index] == '1':
                    assert np.isnan(self.constant[predname])
                    self.constant[predname] = csvv['gamma'][index]
                else:
                    self.predcovars[predname].append(csvv['covarnames'][index])
                    self.predgammas[predname].append(csvv['gamma'][index])

            self.predgammas[predname] = np.array(self.predgammas[predname])

    def get_coefficients(self, covariates, debug=False):
        coefficients = {} # {predname: sum}
        for predname in set(self.prednames):
            if len(self.predgammas[predname]) == 0:
                coefficients[predname] = self.constant[predname]
            else:
                try:
                    coefficients[predname] = self.constant[predname] + np.sum(self.predgammas[predname] * np.array([covariates[covar] for covar in self.predcovars[predname]]))
                    if debug:
                        print predname, self.constant[predname], self.predgammas[predname], np.array([covariates[covar] for covar in self.predcovars[predname]])
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

    def get_curve(self, region, year, covariates={}):
        raise NotImplementedError()

class FarmerCurveGenerator(DelayedCurveGenerator):
    """Handles different adaptation assumptions."""
    def __init__(self, curvegen, covariator, farmer='full', save_curve=True):
        super(FarmerCurveGenerator, self).__init__(curvegen)
        self.covariator = covariator
        self.farmer = farmer
        self.save_curve = save_curve

    def get_next_curve(self, region, year, *args, **kwargs):
        if year < 2015:
            if region not in self.last_curves:
                covariates = self.covariator.get_current(region)
                curve = self.curvegen.get_curve(region, year, covariates)

                if self.save_curve:
                    region_curves[region] = curve

                return curve

            return self.last_curves[region]

        if self.farmer == 'full':
            covariates = self.covariator.get_update(region, year, kwargs['weather'])
            curve = self.curvegen.get_curve(region, year, covariates)
        elif self.farmer == 'noadapt':
            curve = self.last_curves[region]
        elif self.farmer == 'incadapt':
            covariates = self.covariator.get_update(region, year, None)
            curve = self.curvegen.get_curve(region, year, covariates)
        else:
            raise ValueError("Unknown farmer type " + str(self.farmer))

        if self.save_curve:
            region_curves[region] = curve

        return curve

    def get_lincom_terms(self, region, year, predictors={}):
        if year < 2015:
            covariates = self.covariator.get_current(region)
        elif self.farmer == 'full':
            covariates = self.covariator.get_update(region, year, predictors.transform(lambda x: x / 365)) # because was summed
        elif self.farmer == 'noadapt':
            assert False, "Don't have this set of covariates."
        elif self.farmer == 'incadapt':
            covariates = self.covariator.get_update(region, year, None)
            
        return self.curvegen.get_lincom_terms_simple(predictors, covariates)

    def get_csvv_coeff(self):
        return self.curvegen.get_csvv_coeff()

    def get_csvv_vcv(self):
        return self.curvegen.get_csvv_vcv()

class DifferenceCurveGenerator(CurveGenerator):
    """Currently just useful for performing lincom calculations."""
    def __init__(self, one, two, prednames, covarnames, twofunc):
        assert one.indepunits == two.indepunits
        assert one.depenunit = two.depenunit
        super(DifferenceCurveGenerator, self).__init__(one.indepunits, one.depenunit)

        self.one = one
        self.two = two
        self.prednames = prednames
        self.covarnames = covarnames
        self.twofunc = twofunc

    def get_lincom_terms_simple(self, predictors, covariates):
        one_preds = FastDataset.subset(predictors, self.prednames)
        one_covars = {covar: covariates[covar] for covar in self.covarnames}
        one_terms = self.one.get_lincom_terms_simple(one_preds, one_covars)

        two_preds = FastDataset.subset(predictors, map(self.twofunc, self.prednames))
        two_covars = {covar: covariates[self.twofunc(covar)] for covar in self.covarnames}
        two_terms = self.two.get_lincom_terms_simple(two_preds, two_covars)
        
        return one_terms - two_terms
