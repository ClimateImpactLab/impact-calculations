import curvegen
import numpy as np
from openest.generate import formatting, diagnostic, selfdocumented
from openest.generate.smart_curve import TransformCoefficientsCurve

class CoefficientsCurveGenerator(curvegen.CSVVCurveGenerator):
    def __init__(self, curvefunc, indepunits, depenunit, prefix, order, csvv, zerostart=True, betalimits={}):
        self.curvefunc = curvefunc
        if zerostart:
            prednames = [prefix + str(ii) for ii in range(order)]
        else:
            prednames = [prefix + str(ii) if ii > 1 else prefix for ii in range(1, order+1)]

        super(CoefficientsCurveGenerator, self).__init__(prednames, indepunits, depenunit, csvv, betalimits=betalimits)

    def get_curve_parameters(self, region, year, covariates={}):
        allcoeffs = self.get_coefficients(covariates)
        return [allcoeffs[predname] for predname in self.prednames]

    def get_curve(self, region, year, covariates={}):
        mycoeffs = self.get_curve_parameters(region, year, covariates)
        return self.curvefunc(mycoeffs)

class SumCoefficientsCurveGenerator(curvegen.CSVVCurveGenerator):
    def __init__(self, prednames, ds_transforms, transform_descriptions, indepunits, depenunit, csvv, diagprefix='coeff-', betalimits={}):
        super(SumCoefficientsCurveGenerator, self).__init__(prednames, indepunits, depenunit, csvv, betalimits=betalimits)
        self.ds_transforms = ds_transforms
        self.transform_descriptions = transform_descriptions
        self.diagprefix = diagprefix
    
    def get_curve_parameters(self, region, year, covariates={}):
        allcoeffs = self.get_coefficients(covariates)
        return [allcoeffs[predname] for predname in self.prednames]

    def get_curve(self, region, year, covariates={}, recorddiag=True):
        mycoeffs = self.get_curve_parameters(region, year, covariates)

        if recorddiag and diagnostic.is_recording():
            for ii in range(len(self.prednames)):
                diagnostic.record(region, covariates.get('year', 2000), self.diagprefix + self.prednames[ii], mycoeffs[ii])

        return TransformCoefficientsCurve(mycoeffs, [self.ds_transforms[predname] for predname in self.prednames], self.transform_descriptions, self.prednames if recorddiag and diagnostic.is_recording() else None)

    def get_lincom_terms_simple_each(self, predname, covarname, predictors, covariates={}):
        pred = np.sum(predictors[predname]._values)
        covar = covariates[self.csvv['covarnames'][ii]] if self.csvv['covarnames'][ii] != '1' else 1
        return pred * covar

    def format_call(self, lang, *args):
        coeffs = [self.diagprefix + predname for predname in self.prednames]
        coeffreps = [formatting.get_parametername(coeff, lang) for coeff in coeffs]
        predreps = [formatting.get_parametername(predname, lang) for predname in self.prednames]
        transreps = [selfdocumented.get_repstr(self.ds_transforms[predname], lang) for predname in self.prednames]
        transdeps = [dep for predname in self.prednames for dep in selfdocumented.get_dependencies(self.ds_transforms[predname], lang)]

        if lang == 'latex':
            elts = {'main': formatting.FormatElement(r"\sum_{k=1}^%d \beta_k x_k" % len(self.prednames), coeffs + self.prednames + transdeps, is_primitive=True)}
        elif lang == 'julia':
            elts = {'main': formatting.FormatElement("sum(%s)" % ' + '.join(["%s * (%s)" % (coeffreps[ii], transreps[ii]) for ii in range(len(coeffs))]), coeffs + transdeps, is_primitive=True)}

        for ii in range(len(self.prednames)):
            elts[self.prednames[ii]] = formatting.ParameterFormatElement(self.prednames[ii], predreps[ii])
            elts[coeffs[ii]] = formatting.ParameterFormatElement(coeffs[ii], coeffreps[ii])
            elts.update(selfdocumented.format_nomain(self.ds_transforms[self.prednames[ii]], lang))

        return elts
    
class MLECoefficientsCurveGenerator(CoefficientsCurveGenerator):
    def get_coefficients(self, covariates, debug=False):
        coefficients = {} # {predname: beta * exp(gamma z)}
        for predname in set(self.prednames):
            if len(self.predgammas[predname]) == 0:
                coefficients[predname] = np.nan
            else:
                try:
                    coefficients[predname] = self.constant[predname] * np.exp(np.sum(self.predgammas[predname] * np.array([covariates[covar] for covar in self.predcovars[predname]])))
                except Exception as e:
                    print "Available covariates:"
                    print covariates
                    raise e

        return coefficients
