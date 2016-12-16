import re
import numpy as np
from adaptation.adapting_curve import InstantAdaptingStepCurve, BinsIncomeDensityPredictorator, ComatoseInstantAdaptingStepCurve, DumbInstantAdaptingStepCurve
from adaptation import curvegen
from openest.generate.stdlib import *

do_singlebin = True

bin_limits = [-100, -17, -12, -7, -2, 3, 8, 13, 18, 23, 28, 33, 100]
bin_names = ['DayNumber-' + str(bin_limits[bb-1]) + '-' + str(bin_limits[bb]) for bb in range(1, len(bin_limits))]
if do_singlebin:
    predcols = ['DayNumber-', 'log gdppc', 'log popop']
else:
    predcols = bin_names + ['loggdppc', 'logpopop']

prednames = ['bin_nInfC_n17C', 'bin_n17C_n12C', 'bin_n12C_n7C', 'bin_n7C_n2C', 'bin_n2C_3C', 'bin_3C_8C', 'bin_8C_13C', 'bin_13C_18C', 'bin_23C_28C', 'bin_28C_33C', 'bin_33C_InfC', 'meandays_bin_nInfC_n17C', 'meandays_bin_n17C_n12C', 'meandays_bin_n12C_n7C', 'meandays_bin_n7C_n2C', 'meandays_bin_n2C_3C', 'meandays_bin_3C_8C', 'meandays_bin_8C_13C', 'meandays_bin_13C_18C', 'meandays_bin_23C_28C', 'meandays_bin_28C_33C', 'meandays_bin_33C_InfC', 'logpopop_bin_nInfC_n17C', 'logpopop_bin_n17C_n12C', 'logpopop_bin_n12C_n7C', 'logpopop_bin_n7C_n2C', 'logpopop_bin_n2C_3C', 'logpopop_bin_3C_8C', 'logpopop_bin_8C_13C', 'logpopop_bin_13C_18C', 'logpopop_bin_23C_28C', 'logpopop_bin_28C_33C', 'logpopop_bin_33C_InfC', 'loggdppc_bin_nInfC_n17C', 'loggdppc_bin_n17C_n12C', 'loggdppc_bin_n12C_n7C', 'loggdppc_bin_n7C_n2C', 'loggdppc_bin_n2C_3C', 'loggdppc_bin_3C_8C', 'loggdppc_bin_8C_13C', 'loggdppc_bin_13C_18C', 'loggdppc_bin_23C_28C', 'loggdppc_bin_28C_33C', 'loggdppc_bin_33C_InfC']
prednames_ageshare = ['bin_nInfC_n17C', 'bin_n17C_n12C', 'bin_n12C_n7C', 'bin_n7C_n2C', 'bin_n2C_3C', 'bin_3C_8C', 'bin_8C_13C', 'bin_13C_18C', 'bin_23C_28C', 'bin_28C_33C', 'bin_33C_InfC,meandays_bin_nInfC_n17C', 'meandays_bin_n17C_n12C', 'meandays_bin_n12C_n7C', 'meandays_bin_n7C_n2C', 'meandays_bin_n2C_3C', 'meandays_bin_3C_8C', 'meandays_bin_8C_13C', 'meandays_bin_13C_18C', 'meandays_bin_23C_28C', 'meandays_bin_28C_33C', 'meandays_bin_33C_InfC,logpopop_bin_nInfC_n17C', 'logpopop_bin_n17C_n12C', 'logpopop_bin_n12C_n7C', 'logpopop_bin_n7C_n2C', 'logpopop_bin_n2C_3C', 'logpopop_bin_3C_8C', 'logpopop_bin_8C_13C', 'logpopop_bin_13C_18C', 'logpopop_bin_23C_28C', 'logpopop_bin_28C_33C', 'logpopop_bin_33C_InfC,loggdppc_bin_nInfC_n17C', 'loggdppc_bin_n17C_n12C', 'loggdppc_bin_n12C_n7C', 'loggdppc_bin_n7C_n2C', 'loggdppc_bin_n2C_3C', 'loggdppc_bin_3C_8C', 'loggdppc_bin_8C_13C', 'loggdppc_bin_13C_18C', 'loggdppc_bin_23C_28C', 'loggdppc_bin_28C_33C', 'loggdppc_bin_33C_InfC,popshare1_bin_nInfC_n17C', 'popshare1_bin_n17C_n12C', 'popshare1_bin_n12C_n7C', 'popshare1_bin_n7C_n2C', 'popshare1_bin_n2C_3C', 'popshare1_bin_3C_8C', 'popshare1_bin_8C_13C', 'popshare1_bin_13C_18C', 'popshare1_bin_23C_28C', 'popshare1_bin_28C_33C', 'popshare1_bin_33C_InfC,popshare3_bin_nInfC_n17C', 'popshare3_bin_n17C_n12C', 'popshare3_bin_n12C_n7C', 'popshare3_bin_n7C_n2C', 'popshare3_bin_n2C_3C', 'popshare3_bin_3C_8C', 'popshare3_bin_8C_13C', 'popshare3_bin_13C_18C', 'popshare3_bin_23C_28C', 'popshare3_bin_28C_33C', 'popshare3_bin_33C_InfC']

def prepare_interp_raw(csvv, weatherbundle, economicmodel, pvals, farmer='full', ageshare=False):
    if ageshare:
        predgen = covariates.CombinedCovariator([covariates.MeanBinsCovariator(weatherbundle, bin_limits, 8, 15, 2015),
                                                 covariates.EconomicCovariator(economicmodel, 3, 2015),
                                                 covariates.AgeShareCovariator(economicmodel, 3, 2015)])

        assert csvv['L'] == 66
        for ll in range(66):
            assert re.match(prednames_ageshare[ll], csvv['prednames'][ll]) is not None, "{0} ~!= {1}".format(prednames[ll], csvv['prednames'][ll])

        mypredcols = predcols + ['age0-4', 'age65+']
    else:
        predgen = covariates.CombinedCovariator([covariates.MeanBinsCovariator(weatherbundle, bin_limits, 8, 15, 2015),
                                                 covariates.EconomicCovariator(economicmodel, 3, 2015)])

        assert csvv['L'] == 44
        for ll in range(44):
            assert re.match(prednames[ll], csvv['prednames'][ll]) is not None, "{0} ~!= {1}".format(prednames[ll], csvv['prednames'][ll])

        mypredcols = predcols
            
    # Enforce the "backwards" ordering of gdppc and popop: easiest solution is flipping csvv
    oldindices = np.array([3, 2])
    newindices = np.array([2, 3])
    for kk in range(11):
        ##csvv['prednames'][kk + newindices * 11] = csvv['prednames'][kk + oldindices * 11] # python makes tough
        csvv['gamma'][kk + newindices * 11] = csvv['gamma'][kk + oldindices * 11]
        csvv['gammavcv'][kk + newindices * 11, :] = csvv['gammavcv'][kk + oldindices * 11, :]
        csvv['gammavcv'][:, kk + newindices * 11] = csvv['gammavcv'][:, kk + oldindices * 11]

    dependencies = []
    beta_generator = curvegen.make_binned_curve_generator(csvv, bin_limits, mypredcols, do_singlebin, pvals.get_seed())

    curve_get_predictors = lambda region, year, temps: predgen.get_update(region, year, temps)

    if farmer == 'full':
        print "Smart farmer..."
        curve = InstantAdaptingStepCurve(beta_generator, curve_get_predictors, bin_limits)
    elif farmer == 'coma':
        print "Comatose farmer..."
        curve = ComatoseInstantAdaptingStepCurve(beta_generator, curve_get_predictors, bin_limits)
    elif farmer == 'dumb':
        print "Dumb farmer..."
        curve = DumbInstantAdaptingStepCurve(beta_generator, curve_get_predictors, bin_limits)
    else:
        print "Unknown farmer type: " + farmer

    # Collect all baselines
    calculation = Transform(
        YearlyBins(curve, 'deaths/100000people/year'),
        'deaths/100000people/year', 'deaths/person/year', lambda x: x / 1e5,
        'convert to deaths/person/year', "Divide by 100000 to convert to deaths/person/year.")

    baseline_get_predictors = lambda region: predgen.get_baseline(region)

    return calculation, dependencies, baseline_get_predictors
