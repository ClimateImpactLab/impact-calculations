import numpy as np
import csvvfile, curvegen
from openest.generate import diagnostic
from openest.models.curve import ZeroInterceptPolynomialCurve

class PolynomialCurveGenerator(curvegen.CSVVCurveGenerator):
    def __init__(self, indepunits, depenunit, prefix, order, csvv):
        self.order = order
        prednames = [prefix + str(ii) if ii > 1 else prefix for ii in range(1, order+1)]
        super(PolynomialCurveGenerator, self).__init__(prednames, indepunits * order, depenunit, csvv)

    def get_curve(self, region, covariates={}):
        coefficients = self.get_coefficients(covariates)
        yy = [coefficients[predname] for predname in self.prednames]

        for predname in self.prednames:
            diagnostic.record(region, covariates.get('year', 2000), predname, coefficients[predname])

        return ZeroInterceptPolynomialCurve([-np.inf, np.inf], yy)
