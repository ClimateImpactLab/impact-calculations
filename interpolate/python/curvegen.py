import numpy as np
from adaptation import curvegen

def make_binned_curve_generator(surface, predictorsdir, predcols, dependencies, do_singlebin, seed):
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

    return BinnedStepCurveGenerator(xxlimits, allpredcoeffs, do_singlebin)
