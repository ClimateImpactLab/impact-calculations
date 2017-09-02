import numpy as np
import csvvfile, curvegen
from openest.generate import diagnostic
from openest.models.curve import ZeroInterceptPolynomialCurve, CubicSplineCurve

class PolynomialCurveGenerator(curvegen.CSVVCurveGenerator):
    def __init__(self, indepunits, depenunit, prefix, order, csvv, diagsuffix=''):
        self.order = order
        prednames = [prefix + str(ii) if ii > 1 else prefix for ii in range(1, order+1)]
        super(PolynomialCurveGenerator, self).__init__(prednames, indepunits * order, depenunit, csvv)
        self.diagsuffix = diagsuffix

    def get_curve(self, region, year, covariates={}, recorddiag=True, **kwargs):
        coefficients = self.get_coefficients(covariates)
        yy = [coefficients[predname] for predname in self.prednames]

        if recorddiag and diagnostic.is_recording():
            for predname in self.prednames:
                diagnostic.record(region, covariates.get('year', 2000), self.diagsuffix + predname, coefficients[predname])

        return ZeroInterceptPolynomialCurve([-np.inf, np.inf], yy)

    def get_lincom_terms(self, predictors={}, covariates={}):
        # Return in the order of the CSVV
        terms = []
        for ii in range(len(csvv['prednames'])):
            pred = predictors[csvv['prednames'][ii]]
            covar = covariates[csvv['covarnames'][ii]]
            terms.append(pred * covar)

        return np.array(terms)

    def get_csvv_coeff(self):
        return csvv['gamma']

    def get_csvv_vcv(self):
        return csvv['vcv']

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
                diagnostic.record(region, covariates.get('year', 2000), predname, coefficients[predname])

        return CubicSplineCurve(self.knots, yy)
