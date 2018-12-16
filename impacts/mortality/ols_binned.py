import re
import numpy as np
from adaptation import csvvfile, curvegen, curvegen_step, covariates
from interpret import configs
from openest.models.curve import StepCurve, OtherClippedCurve
from openest.generate.stdlib import *

bin_limits = [-np.inf, -13, -8, -3, 2, 7, 12, 17, 22, 27, 32, np.inf]

def prepare_interp_raw(csvv, weatherbundle, economicmodel, pvals, farmer='full', config={}):
    covariator = covariates.CombinedCovariator([covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 2015, config=configs.merge(config, 'climcovar'), varindex=0), {'climtas': 'tas'}),
                                                covariates.EconomicCovariator(economicmodel, 2015, config=configs.merge(config, 'econcovar'))])
    print "CSVV Len: %d" % len(csvv['covarnames'])

    # Don't collapse: already collapsed in allmodels
    #csvvfile.collapse_bang(csvv, qvals.get_seed())

    curr_curvegen = curvegen_step.BinnedStepCurveGenerator(bin_limits, ['days / year'] * (len(bin_limits) - 1),
                                                      '100,000 * death/population', csvv)
    farm_curvegen = curvegen.FarmerCurveGenerator(curr_curvegen, covariator, farmer)

    climtas_effect_curve = StepCurve(bin_limits, np.array([csvvfile.get_gamma(csvv, tasvar, 'climtas') for tasvar in csvvfile.binnames(bin_limits, 'bins')]))

    def transform_climtas_effect(region, curve):
        return OtherClippedCurve(curve, climtas_effect_curve, clipy=curr_curvegen.min_betas[region])

    climtas_effect_curvegen = curvegen.TransformCurveGenerator(transform_climtas_effect, farm_curvegen)

    # Collect all baselines
    calculation = Transform(
        AuxillaryResult(
            YearlyBins('100,000 * death/population', farm_curvegen, "the mortality response curve",
                       lambda x: x[1:]), # drop tas, leaving only bins
            YearlyBins('100,000 * death/population', climtas_effect_curvegen, "climtas effect after clipping",
                       lambda x: x[1:], norecord=True), 'climtas_effect'),
        '100,000 * death/population', 'deaths/person/year', lambda x: x / 1e5,
        'convert to deaths/person/year', "Divide by 100000 to convert to deaths/person/year.")

    return calculation, [], covariator.get_current
