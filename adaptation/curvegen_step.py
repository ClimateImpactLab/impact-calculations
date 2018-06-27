import numpy as np
import csvvfile, curvegen
from openest.models.curve import StepCurve

min_betas = {} # {region: min_beta}

class BinnedStepCurveGenerator(curvegen.CSVVCurveGenerator):
    def __init__(self, xxlimits, indepunits, depenunit, csvv):
        self.xxlimits = xxlimits
        prednames = csvvfile.binnames(xxlimits, 'bins')
        super(BinnedStepCurveGenerator, self).__init__(prednames, indepunits, depenunit, csvv)
        self.min_betas = {}

    def get_curve(self, region, year, covariates={}):
        coefficients = self.get_coefficients(covariates)
        yy = [coefficients[predname] for predname in self.prednames]

        min_beta = self.min_betas.get(region, None)

        if min_beta is None:
            self.min_betas[region] = np.minimum(0, np.nanmin(np.array(yy)[4:-2]))
        else:
            yy = np.maximum(min_beta, yy)

        return StepCurve(self.xxlimits, yy)

