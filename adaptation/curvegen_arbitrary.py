import curvegen
from openest.models import curve
import numpy as np

class CoefficientsCurveGenerator(curvegen.CSVVCurveGenerator):
    def __init__(self, curvefunc, indepunits, depenunit, prednames, csvv):
        self.curvefunc = curvefunc
        super(CoefficientsCurveGenerator, self).__init__(prednames, indepunits, depenunit, csvv)

    def get_curve_parameters(self, region, year, covariates={}):
        allcoeffs = self.get_coefficients(covariates)
        return [allcoeffs[predname] for predname in self.prednames]

    def get_curve(self, region, year, covariates={}):
        mycoeffs = self.get_curve_parameters(region, year, covariates)
        return self.curvefunc(mycoeffs)

class ParameterHolderCurve(curve.UnivariateCurve):
    def __init__(self, params):
        super(ParameterHolderCurve, self).__init__([-np.inf, np.inf])
        self.params = params
    
class MLECoefficientsCurveGenerator(CoefficientsCurveGenerator):
    def __init__(self, curvefunc, indepunits, depenunit, prednames, csvv, zerostart=True):
        if zerostart:
            prednames = [prefix + str(ii) for ii in range(order)]
        else:
            prednames = [prefix + str(ii) if ii > 1 else prefix for ii in range(1, order+1)]
        super(MLECoefficientsCurveGenerator, self).__init__(curvefunc, indepunits, depenunit, prednames, csvv)

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

