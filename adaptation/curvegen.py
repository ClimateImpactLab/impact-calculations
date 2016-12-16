import numpy as np
from openest.models.curve import StepCurve
from scipy.stats import multivariate_normal
import csvvfile



class BinnedStepCurveGenerator(object):
    def __init__(self, xxlimits, predcoeffs, predcols, do_singlebin):
        self.xxlimits = xxlimits
        self.predcoeffs = predcoeffs
        self.do_singlebin = do_singlebin
        self.predcols = predcols

    def get_curve(self, predictors, min_beta):
        yy = []
        for ii in range(len(self.predcoeffs)):
            if np.isnan(self.predcoeffs[ii][0]):
                yy.append(np.nan) # may not have all coeffs for dropped bin
            else:
                bincol = 'DayNumber-' + str(self.xxlimits[ii]) + '-' + str(self.xxlimits[ii+1])
                predictors_self = np.array([predictors[predcol] if predcol[-1] != '-' else predictors[bincol] for predcol in self.predcols])
                yy.append(self.predcoeffs[ii][0] + np.sum(self.predcoeffs[ii][1:] * predictors_self))

        if min_beta is not None:
            yy = np.maximum(min_beta, yy)

        return StepCurve(self.xxlimits, yy)

def make_binned_curve_generator(csvv, xxlimits, predcols, do_singlebin, seed):
    if seed is None:
        params = csvv['gamma']
    else:
        params = multivariate_normal.rvs(csvv['gamma'], csvv['gammavcv'])

    # Reorganize params into sets of L
    gammas = csvvfile.by_predictor_kl(csvv, params, (len(predcols) + 1))
    # Insert dropped bin: hard coded for now
    before_dropped = np.flatnonzero(np.array(xxlimits) == 18)[0]
    gammas = gammas[:before_dropped] + [np.array([np.nan] * (len(predcols) + 1))] + gammas[before_dropped:]

    return BinnedStepCurveGenerator(xxlimits, gammas, predcols, do_singlebin)
