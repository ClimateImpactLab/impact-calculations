import re
import numpy as np
from adaptation.adapting_curve import InstantAdaptingStepCurve, BinsIncomeDensityPredictorator, ComatoseInstantAdaptingStepCurve, DumbInstantAdaptingStepCurve
from adaptation import curvegen
from openest.generate.stdlib import *

do_singlebin = True

if do_singlebin:
    predcols = ['meandays_self', 'log gdppc', 'log popop']
else:
    predcols = ['meandays_nInfC_n17C', 'meandays_n17C_n12C', 'meandays_n12C_n7C', 'meandays_n7C_n2C', 'meandays_n2C_3C', 'meandays_3C_8C', 'meandays_8C_13C', 'meandays_13C_18C', 'meandays_23C_28C', 'meandays_28C_33C', 'meandays_33C_InfC', 'log gdppc', 'log popop']
bin_limits = [-np.inf, -17, -12, -7, -2, 3, 8, 13, 18, 23, 28, 33, np.inf]

prednames = ['bin_nInfC_n17C', 'bin_n17C_n12C', 'bin_n12C_n7C', 'bin_n7C_n2C', 'bin_n2C_3C', 'bin_3C_8C', 'bin_8C_13C', 'bin_13C_18C', 'bin_23C_28C', 'bin_28C_33C', 'bin_33C_InfC', 'meandays_bin_nInfC_n17C', 'meandays_bin_n17C_n12C', 'meandays_bin_n12C_n7C', 'meandays_bin_n7C_n2C', 'meandays_bin_n2C_3C', 'meandays_bin_3C_8C', 'meandays_bin_8C_13C', 'meandays_bin_13C_18C', 'meandays_bin_23C_28C', 'meandays_bin_28C_33C', 'meandays_bin_33C_InfC', 'logpopop_bin_nInfC_n17C', 'logpopop_bin_n17C_n12C', 'logpopop_bin_n12C_n7C', 'logpopop_bin_n7C_n2C', 'logpopop_bin_n2C_3C', 'logpopop_bin_3C_8C', 'logpopop_bin_8C_13C', 'logpopop_bin_13C_18C', 'logpopop_bin_23C_28C', 'logpopop_bin_28C_33C', 'logpopop_bin_33C_InfC', 'loggdppc_bin_nInfC_n17C', 'loggdppc_bin_n17C_n12C', 'loggdppc_bin_n12C_n7C', 'loggdppc_bin_n7C_n2C', 'loggdppc_bin_n2C_3C', 'loggdppc_bin_3C_8C', 'loggdppc_bin_8C_13C', 'loggdppc_bin_13C_18C', 'loggdppc_bin_23C_28C', 'loggdppc_bin_28C_33C', 'loggdppc_bin_33C_InfC']

def prepare_interp_raw(csvv, weatherbundle, economicmodel, pvals, farmer='full'):
    predgen = BinsIncomeDensityPredictorator(weatherbundle, economicmodel, bin_limits, 8, 15, 3, 2015)

    assert csvv['L'] == 44
    for ll in range(44):
        assert re.match(prednames[ll], csvv['prednames'][ll]) is not None, "{0} ~!= {1}".format(prednames[ll], csvv['prednames'][ll])

    # Enforce the "backwards" ordering of gdppc and popop: easiest solution is flipping csvv
    oldindices = np.array([3, 2])
    newindices = np.array([2, 3])
    for kk in range(11):
        ##csvv['prednames'][kk + newindices * 11] = csvv['prednames'][kk + oldindices * 11] # python makes tough
        csvv['gamma'][kk + newindices * 11] = csvv['gamma'][kk + oldindices * 11]
        csvv['gammavcv'][kk + newindices * 11, :] = csvv['gammavcv'][kk + oldindices * 11, :]
        csvv['gammavcv'][:, kk + newindices * 11] = csvv['gammavcv'][:, kk + oldindices * 11]

    dependencies = []
    beta_generator = curvegen.make_binned_curve_generator(csvv, bin_limits, predcols, do_singlebin, pvals.get_seed())

    curve_get_predictors = lambda region, year, temps: predgen.get_update(region, year, temps)[0]

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
