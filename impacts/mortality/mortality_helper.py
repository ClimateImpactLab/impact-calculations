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

def prepare_interp_raw(csvv, weatherbundle, economicmodel, pvals, get_data, farmer='full'):
    predgen = BinsIncomeDensityPredictorator(weatherbundle, economicmodel, bin_limits, 8, 15, 3, 2015)

    assert csvv['L'] == 4 and csvv['K'] == 11
    assert csvv['prednames'] == ['const', 'meandays', 'logpopop', 'loggdppc']
    # Enforce the "backwards" ordering: easiest solution is flipping csvv
    csvv['prednames'][3], csvv['prednames'][2] = csvv['prednames'][2], csvv['prednames'][3]
    for kk in range(11):
        csvv['gamma'][kk + 4 * 3], csvv['gamma'][kk + 4 * 2] = csvv['gamma'][kk + 4 * 2], csvv['gamma'][kk + 4 * 3]
        csvv['gammavcv'][kk + 4 * 3, :], csvv['gammavcv'][kk + 4 * 2, :] = csvv['gammavcv'][kk + 4 * 2, :], csvv['gammavcv'][kk + 4 * 3, :]
        csvv['gammavcv'][:, kk + 4 * 3], csvv['gammavcv'][:, kk + 4 * 2] = csvv['gammavcv'][:, kk + 4 * 2], csvv['gammavcv'][:, kk + 4 * 3]

    dependencies = []
    beta_generator = curvegen.make_curve_generator(csvv, bin_limits, predcols, do_singlebin, pvals.get_seed())

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

    return calculation, dependencies, curve, baseline_get_predictors
