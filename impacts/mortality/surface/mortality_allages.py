import os
from impacts import weather
from adapting_curve import AdaptingStepCurve, TemperatureIncomePredictorator
import curvegen, surface_space, surface_time
from datastore import library
from openest.generate.stdlib import *

def prepare_weathered_raw(weatherbundle, do_median):
    predgen = TemperatureIncomePredictorator(weatherbundle, 10, 2015)

    dependencies = []
    beta_generator = curvegen.make_binned_curve_generator(surface_space, dependencies, do_median=do_median)
    gamma_generator = curvegen.make_binned_curve_generator(surface_time, dependencies, do_median=do_median)

    curve_get_predictors = lambda region, year, temps: predgen.get_update(region, year, temps)
    error("Need a different curve for each region!")
    curve = AdaptingStepCurve(beta_generator, gamma_generator, curve_get_predictors)

    # Load the baseline data
    mortality_rates, mortality_version = library.get_data('mortality-deathrates', 'deaths/person')

    # Collect all baselines
    calculation = Scale(
        YearlyDayBins(curve, 'portion'),
        mortality_rates, 'portion', 'deaths/person')

    baseline_get_predictors = lambda region: predgen.get_baseline(region)

    return calculation, dependencies, curve, baseline_get_predictors
