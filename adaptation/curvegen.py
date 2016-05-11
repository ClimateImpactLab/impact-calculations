import numpy as np
from openest.models.curve import StepCurve

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

def make_curve_generator(surface, predictorsdir, predcols, dependencies, do_singlebin, seed):
    # Read in the predictors
    binlos = []
    binhis = []
    meanses = []
    serrses = []
    predictorses = []
    for binlo, binhi, means, serrs, predictors in surface.all_predictors(predictorsdir, predcols, dependencies, allowinf=True):
        binlos.append(binlo)
        binhis.append(binhi)
        meanses.append(means)
        serrses.append(serrs)
        predictorses.append(predictors)

    allcoeffs = surface.standard(meanses, serrses, predictorses, seed)
    print allcoeffs
    predcoefflen = len(predictorses[0][0]) + 1 # +1 for intercept
    predcoeffs = []
    for jj in range(0, len(allcoeffs), predcoefflen):
        predcoeffs.append(allcoeffs[jj:jj+predcoefflen])

    # Create a consistent order, and fill in dropped bin
    allxx = set(binlos)
    allxx.update(binhis)
    xxlimits = sorted(allxx)

    allpredcoeffs = []
    for binlo in xxlimits[:-1]:
        try:
            ii = binlos.index(binlo)
            allpredcoeffs.append(np.array(predcoeffs[ii]))
        except:
            allpredcoeffs.append(np.array([np.nan] * 2)) # intercept and predictor

    return StepCurveGenerator(xxlimits, allpredcoeffs, do_singlebin)
