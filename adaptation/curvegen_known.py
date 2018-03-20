import numpy as np
import csvvfile, curvegen
from openest.generate import diagnostic, formatting
from openest.models.curve import ZeroInterceptPolynomialCurve, CubicSplineCurve

class PolynomialCurveGenerator(curvegen.CSVVCurveGenerator):
    def __init__(self, indepunits, depenunit, prefix, order, csvv, diagprefix='coeff-'):
        self.order = order
        prednames = [prefix + str(ii) if ii > 1 else prefix for ii in range(1, order+1)]
        super(PolynomialCurveGenerator, self).__init__(prednames, indepunits * order, depenunit, csvv)
        self.diagprefix = diagprefix

    def get_curve(self, region, year, covariates={}, recorddiag=True, **kwargs):
        coefficients = self.get_coefficients(covariates)
        yy = [coefficients[predname] for predname in self.prednames]

        if recorddiag and diagnostic.is_recording():
            for predname in self.prednames:
                diagnostic.record(region, year, self.diagprefix + predname, coefficients[predname])

        return ZeroInterceptPolynomialCurve([-np.inf, np.inf], yy)

    def get_lincom_terms_simple(self, predictors={}, covariates={}):
        # Return in the order of the CSVV
        terms = []
        for ii in range(len(self.csvv['prednames'])):
            predname = self.csvv['prednames'][ii]
            if predname not in predictors._variables.keys():
                predname = predname[:-1] + '-poly-' + predname[-1]
                
            pred = predictors[predname]._values
            covar = covariates[self.csvv['covarnames'][ii]] if self.csvv['covarnames'][ii] != '1' else 1
            terms.append(pred * covar)

        return np.array(terms)

    def get_csvv_coeff(self):
        return self.csvv['gamma']

    def get_csvv_vcv(self):
        return self.csvv['gammavcv']

    def format_call(self, lang, *args):
        if lang == 'latex':
            return {'main': formatting.FormatElement(r"\sum_{k=1}^%d \beta_k %s^k" % (self.order, args[0]), self.depenunit, is_primitive=True)}
        elif lang == 'julia':
            return {'main': formatting.FormatElement("beta[1] * " + args[0] + ' + ' + ' + '.join(["beta[%d] * %s^%d" % (order, args[0], order) for order in range(2, self.order + 1)]), self.depenunit, is_primitive=True)}

class CubicSplineCurveGenerator(curvegen.CSVVCurveGenerator):
    def __init__(self, indepunits, depenunit, prefix, knots, csvv):
        self.knots = knots
        prednames = [prefix + str(ii) for ii in range(len(knots)-1)]
        super(CubicSplineCurveGenerator, self).__init__(prednames, indepunits, depenunit, csvv)

    def get_curve(self, region, year, covariates={}, recorddiag=True, **kwargs):
        coefficients = self.get_coefficients(covariates)
        yy = [coefficients[predname] for predname in self.prednames]

        if recorddiag and diagnostic.is_recording():
            for predname in self.prednames:
                diagnostic.record(region, year, predname, coefficients[predname])

        return CubicSplineCurve(self.knots, yy)
