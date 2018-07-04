import numpy as np
from openest.generate.curvegen import *
from openest.generate import checks, fast_dataset, formatting

region_curves = {}

class CSVVCurveGenerator(CurveGenerator):
    def __init__(self, prednames, indepunits, depenunit, csvv, betalimits={}):
        super(CSVVCurveGenerator, self).__init__(indepunits, depenunit)

        assert isinstance(prednames, list) or isinstance(prednames, set) or isinstance(prednames, tuple)
        self.prednames = prednames
        self.csvv = csvv
        self.betalimits = betalimits

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
            self.predcovars[predname] = []
            self.predgammas[predname] = []

            indices = [ii for ii, xx in enumerate(csvv['prednames']) if xx == predname]
            for index in indices:
                if csvv['covarnames'][index] == '1':
                    assert predname not in self.constant
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
                    coefficients[predname] = self.constant.get(predname, 0) + np.sum(self.predgammas[predname] * np.array([covariates[covar] for covar in self.predcovars[predname]]))
                    if predname in self.betalimits and not np.isnan(coefficients[predname]):
                        coefficients[predname] = min(max(self.betalimits[predname][0], coefficients[predname]), self.betalimits[predname][1])
                    
                    if debug:
                        print predname, coefficients[predname], self.constant.get(predname, 0), self.predgammas[predname], np.array([covariates[covar] for covar in self.predcovars[predname]])
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
            covariates = self.covariator.offer_update(region, year, kwargs['weather'])
            curve = self.curvegen.get_curve(region, year, covariates)
        elif self.farmer == 'noadapt':
            curve = self.last_curves[region]
        elif self.farmer == 'incadapt':
            covariates = self.covariator.offer_update(region, year, None)
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
            covariates = self.covariator.offer_update(region, year, predictors.transform(lambda x: x / 365)) # because was summed
        elif self.farmer == 'noadapt':
            assert False, "Don't have this set of covariates."
        elif self.farmer == 'incadapt':
            covariates = self.covariator.offer_update(region, year, None)
            
        return self.curvegen.get_lincom_terms_simple(predictors, covariates)

    def get_csvv_coeff(self):
        return self.curvegen.get_csvv_coeff()

    def get_csvv_vcv(self):
        return self.curvegen.get_csvv_vcv()

class DifferenceCurveGenerator(CurveGenerator):
    """Currently just useful for performing lincom calculations."""
    def __init__(self, one, two, prednames, covarnames, onefunc, twofunc):
        assert one.indepunits == two.indepunits
        assert one.depenunit == two.depenunit
        super(DifferenceCurveGenerator, self).__init__(one.indepunits, one.depenunit)

        self.one = one
        self.two = two
        self.prednames = prednames
        self.covarnames = covarnames
        self.onefunc = onefunc
        self.twofunc = twofunc

    def get_lincom_terms_simple(self, predictors, covariates):
        one_preds = fast_dataset.FastDataset.subset(predictors, map(self.onefunc, self.prednames))
        one_covars = {covar: covariates[self.onefunc(covar)] if covar != '1' else 1 for covar in self.covarnames}
        one_terms = self.one.get_lincom_terms_simple(one_preds, one_covars)

        two_preds = fast_dataset.FastDataset.subset(predictors, map(self.twofunc, self.prednames)).rename({self.twofunc(name): name for name in set(self.prednames)})
        two_covars = {covar: covariates[self.twofunc(covar)] if covar != '1' else 1 for covar in self.covarnames}
        two_terms = self.two.get_lincom_terms_simple(two_preds, two_covars)
        
        return one_terms - two_terms

    def get_csvv_coeff(self):
        return self.one.get_csvv_coeff()

    def get_csvv_vcv(self):
        return self.one.get_csvv_vcv()
        
    def format_call(self, lang, *args):
        equation_one = self.one.format_call(lang, *args)
        equation_two = self.two.format_call(lang, *args)
        
        result = {}
        result.update(equation_one)
        result.update(equation_two)
        result['main'] = formatting.FormatElement("%s - %s" % (equation_one['main'].repstr, equation_two['main'].repstr), self.one.dependencies + self.two.dependencies)
        return result

class SumByTimeCurveGenerator(CurveGenerator):
    def __init__(self, csvvcurvegen, coeffrepls, variable):
        super(SumByTimeCurveGenerator, self).__init__(csvvcurvegen[0].indepunits, csvvcurvegen[0].depenunit)
        curvegens = []
        for coeffrepl in coeffrepls:
            curvegen = copy.copy(csvvcurvegen)
            curvegen.predname = curvegen.predname.replace('#', coeffrepl)
            curvegens.append(curvegen)
        
        self.curvegens = curvegens
        self.variable = variable

    def get_curve(self, region, year, **kwargs):
        curves = [curvegen(region, year, **kwargs) for curvegen in self.curvegens]
        return SumByTimeCurve(curves, self.variable)

TODO:
1. How is it that poly curve isn't given a dataset
2. Shouldn't sumbytimecurve pass a dataset to its subs?
3. Can I use that to maintain the pr-#, pr2-# setup?
