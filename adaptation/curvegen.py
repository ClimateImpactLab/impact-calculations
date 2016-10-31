import numpy as np
from openest.models.curve import StepCurve
from scipy.stats import multivariate_normal
import csvvfile

class StepCurveGenerator(object):
    def __init__(self, xxlimits, predcoeffs, do_singlebin):
        self.xxlimits = xxlimits
        self.predcoeffs = predcoeffs
        self.do_singlebin = do_singlebin

    def get_curve(self, predictors, min_beta):
        if self.do_singlebin:
            assert len(predictors) == (len(self.xxlimits) - 2) + 2, "Wrong number of predictors: " + str(len(predictors)) + " vs. " + str((len(self.xxlimits) - 2) + 2) # Bins... except dropped, GDPPC, PoPoP
        yy = []
        preddeltaii = 0 # Set to -1 after dropped bin; used for do_singlebin
        for ii in range(len(self.predcoeffs)):
            if np.isnan(self.predcoeffs[ii][0]):
                yy.append(np.nan) # may not have all coeffs for dropped bin
                preddeltaii = -1 # one fewer meandays than bins
            else:
                if self.do_singlebin:
                    predictors_self = np.array([predictors[ii + preddeltaii], predictors[-2], predictors[-1]])
                    yy.append(self.predcoeffs[ii][0] + np.sum(self.predcoeffs[ii][1:] * predictors_self))
                else:
                    yy.append(self.predcoeffs[ii][0] + np.sum(self.predcoeffs[ii][1:] * np.array(predictors)))

        if min_beta is not None:
            yy = np.maximum(min_beta, yy)

        return StepCurve(self.xxlimits, yy)

def make_curve_generator(csvv, xxlimits, predcols, do_singlebin, seed):
    if seed is None:
        params = csvv['gamma']
    else:
        params = multivariate_normal.rvs(csvv['gamma'], csvv['gannavcv'])

    # Reorganize params into sets of L
    gammas = csvvfile.by_predictor(csvv, params)
    # Insert dropped bin: hard coded for now
    before_dropped = np.where(np.array(xxlimits) == 18)[0]
    print before_dropped
    gammas = gammas[:before_dropped] + [np.array([np.nan] * csvv['L'])] + gammas[before_dropped:]

    return StepCurveGenerator(xxlimits, gammas, do_singlebin)
