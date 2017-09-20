import re
import numpy as np
from adaptation import csvvfile, curvegen, curvegen_step, covariates
from openest.generate.stdlib import *

bin_limits = [-np.inf, -13, -8, -3, 2, 7, 12, 17, 22, 27, 32, np.inf]

def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full', ageshare=False, config={}):
    if ageshare:
        covariator = covariates.CombinedCovariator([covariates.MeanBinsCovariator(weatherbundle, bin_limits, 8, 2015, config=config.get('climcovar', {})),
                                                    covariates.EconomicCovariator(economicmodel, 2015, config=config.get('econcovar', {})),
                                                    covariates.AgeShareCovariator(economicmodel, 2015, config=config.get('econcovar', {}))])

        assert len(csvv['covarnames']) == 60
    else:
        covariator = covariates.CombinedCovariator([covariates.MeanBinsCovariator(weatherbundle, bin_limits, 8, 2015, config=config.get('climcovar', {})),
                                                    covariates.EconomicCovariator(economicmodel, 2015, config=config.get('econcovar', {}))])

        assert len(csvv['covarnames']) == 40

    csvvfile.collapse_bang(csvv, qvals.get_seed())

    curr_curvegen = curvegen_step.BinnedStepCurveGenerator(bin_limits, ['days / year'] * (len(bin_limits) - 1),
                                                      '100,000 * death/population', csvv)
    farm_curvegen = curvegen.FarmerCurveGenerator(curr_curvegen, covariator, farmer)

    # Collect all baselines
    calculation = Transform(
        YearlyBins('100,000 * death/population', farm_curvegen, "the mortality response curve"),
        '100,000 * death/population', 'deaths/person/year', lambda x: x / 1e5,
        'convert to deaths/person/year', "Divide by 100000 to convert to deaths/person/year.")

    return calculation, [], covariator.get_current_args
