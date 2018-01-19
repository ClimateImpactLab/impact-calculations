import curvegen
import numpy as np
from openest.generate import formatting, diagnostic
from openest.generate.smart_curve import TransformCoefficientsCurve

class CoefficientsCurveGenerator(curvegen.CSVVCurveGenerator):
    def __init__(self, curvefunc, indepunits, depenunit, prefix, order, csvv, zerostart=True):
        self.curvefunc = curvefunc
        if zerostart:
            prednames = [prefix + str(ii) for ii in range(order)]
        else:
            prednames = [prefix + str(ii) if ii > 1 else prefix for ii in range(1, order+1)]

        super(CoefficientsCurveGenerator, self).__init__(prednames, indepunits, depenunit, csvv)

    def get_curve_parameters(self, region, year, covariates={}):
        allcoeffs = self.get_coefficients(covariates)
        return [allcoeffs[predname] for predname in self.prednames]

    def get_curve(self, region, year, covariates={}):
        mycoeffs = self.get_curve_parameters(region, year, covariates)
        return self.curvefunc(mycoeffs)

class SumCoefficientsCurveGenerator(curvegen.CSVVCurveGenerator):
    def __init__(self, prednames, ds_transforms, transform_descriptions, indepunits, depenunit, csvv, diagprefix='coeff-'):
        super(SumCoefficientsCurveGenerator, self).__init__(prednames, indepunits, depenunit, csvv)
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

    def format_call(self, lang, *args):
        if lang == 'latex':
            elts = {'main': formatting.FormatElement(r"\sum_{k=1}^%d \beta_k x_k" % len(self.prednames), self.depenunit, is_primitive=True)}
        elif lang == 'julia':
            elts = {'main': formatting.FormatElement("sum(beta .* [%s])" % ', '.join("x_%d" % ii for ii in range(len(self.prednames))), self.depenunit, is_primitive=True)}

        for ii in range(len(self.prednames)):
            elts['x_%d' % ii] = formatting.FormatElement("%s (%s)" % (self.prednames[ii], self.transform_descriptions[ii]), self.indepunits[ii])

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
