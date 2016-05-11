import numpy as np
from adapting_curve import InstantAdaptingStepCurve, BinsIncomeDensityPredictorator, ComatoseInstantAdaptingStepCurve, DumbInstantAdaptingStepCurve
import curvegen, surface_space, mortality_helper
from openest.generate.stdlib import *

do_singlebin = True

if do_singlebin:
    predcols = ['meandays_self', 'log gdppc', 'log popop']
else:
    predcols = ['meandays_nInfC_n17C', 'meandays_n17C_n12C', 'meandays_n12C_n7C', 'meandays_n7C_n2C', 'meandays_n2C_3C', 'meandays_3C_8C', 'meandays_8C_13C', 'meandays_13C_18C', 'meandays_23C_28C', 'meandays_28C_33C', 'meandays_33C_InfC', 'log gdppc', 'log popop']

def prepare_interp_raw(predictorsdir, weatherbundle, economicmodel, pvals, get_data, farmer='full'):
    predgen = BinsIncomeDensityPredictorator(weatherbundle, economicmodel, [-np.inf, -17, -12, -7, -2, 3, 8, 13, 18, 23, 28, 33, np.inf], 8, 15, 3, 2015)

    dependencies = []
    beta_generator = curvegen.make_curve_generator(surface_space, predictorsdir, predcols, dependencies, do_singlebin, pvals.get_seed())

    curve_get_predictors = lambda region, year, temps: predgen.get_update(region, year, temps)[0]

    if farmer == 'full':
        curve = InstantAdaptingStepCurve(beta_generator, curve_get_predictors)
    elif farmer == 'coma':
        curve = ComatoseInstantAdaptingStepCurve(beta_generator, curve_get_predictors)
    elif farmer == 'dumb':        
        curve = DumbInstantAdaptingStepCurve(beta_generator, curve_get_predictors)
    else:
        print "Unknown farmer type: " + farmer

    # Collect all baselines
    calculation = Transform(
        YearlyDayBins(curve, 'deaths/100000people/year'),
        'deaths/100000people/year', 'deaths/person/year', lambda x: x / 1e5,
        'convert to deaths/person/year', "Divide by 100000 to convert to deaths/person/year.")

    baseline_get_predictors = lambda region: predgen.get_baseline(region)

    return calculation, dependencies, curve, baseline_get_predictors
