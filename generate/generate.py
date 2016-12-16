import sys, os, itertools, importlib, shutil, csv
import loadmodels
import weather, effectset
from adaptation import adapting_curve, curvegenv2

module = sys.argv[2]
outputdir = sys.argv[3]

def iterate_median():
    for clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel in loadmodels.random_order(mod.bundle_iterator):
        pvals = effectset.ConstantPvals(.5)
        yield 'median', pvals, clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel

def iterate_montecarlo():
    for batch in itertools.count():
        for clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel in loadmodels.random_order(mod.bundle_iterator):
            pvals = effectset.OnDemandRandomPvals()
            yield 'batch' + str(batch), pvals, clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel

def iterate_single():
    clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel = loadmodels.single(mod.bundle_iterator)
    pvals = effectset.ConstantPvals(.5)

    # Check if this already exists and delete if so
    targetdir = os.path.join(outputdir, 'single', clim_scenario, clim_model, econ_model, econ_scenario)
    if os.path.exists(targetdir):
        shutil.rmtree(targetdir)

    yield 'single', pvals, clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel

def iterate_writebins():
    with open(module + "-allbins.csv", 'w') as fp:
        writer = csv.writer(fp)
        writer.writerow(['region', 'year', 'model', 'result', 'bin_nInfC_n17C', 'bin_n17C_n12C', 'bin_n12C_n7C', 'bin_n7C_n2C', 'bin_n2C_3C', 'bin_3C_8C', 'bin_8C_13C', 'bin_13C_18C', 'bin_18C_23C', 'bin_23C_28C', 'bin_28C_33C', 'bin_33C_InfC'])

    with open(module + "-allpreds.csv", 'w') as fp:
        writer = csv.writer(fp)
        writer.writerow(['region', 'year', 'model', 'meandays_nInfC_n17C', 'meandays_n17C_n12C', 'meandays_n12C_n7C', 'meandays_n7C_n2C', 'meandays_n2C_3C', 'meandays_3C_8C', 'meandays_8C_13C', 'meandays_13C_18C', 'meandays_23C_28C', 'meandays_28C_33C', 'meandays_33C_InfC', 'log gdppc', 'log popop'])

    for allvals in iterate_single():
        yield allvals

def iterate_writevals():
    with open(module + "-allcoeffs.csv", 'w') as fp:
        writer = csv.writer(fp)
        writer.writerow(['region', 'year', 'model', 'result', 'tasmax', 'tasmax2', 'tasmax3', 'tasmax4', 'belowzero'])

    with open(module + "-allpreds.csv", 'w') as fp:
        writer = csv.writer(fp)
        writer.writerow(['region', 'year', 'model', 'meantas', 'log gdppc', 'log popop'])

    for allvals in iterate_single():
        yield allvals

def binresult_callback(region, year, result, calculation, model):
    with open(module + "-allbins.csv", 'a') as fp:
        writer = csv.writer(fp)
        curve = adapting_curve.region_stepcurves[region].curr_curve
        writer.writerow([region, year, model, result[0]] + list(curve.yy))

def binpush_callback(region, year, application, get_predictors, model):
    with open(module + "-allpreds.csv", 'a') as fp:
        writer = csv.writer(fp)
        predictors = get_predictors(region)[0]

        bin_limits = [-100, -17, -12, -7, -2, 3, 8, 13, 18, 23, 28, 33, 100]
        bin_names = ['DayNumber-' + str(bin_limits[bb-1]) + '-' + str(bin_limits[bb]) for bb in range(1, len(bin_limits))]
        covars = bin_names + ['loggdppc', 'logpopop']
        if 'age0-4' in predictors:
            covars += ['age0-4', 'age65+']

        writer.writerow([region, year, model] + [predictors[covar] for covar in covars])

def valresult_callback(region, year, result, calculation, model):
    with open(module + "-allcoeffs.csv", 'a') as fp:
        writer = csv.writer(fp)
        ccs = curvegenv2.region_polycurves[region].curr_curve.ccs
        writer.writerow([region, year, model, result[0]] + list(ccs))

def valpush_callback(region, year, application, get_predictors, model):
    with open(module + "-allpreds.csv", 'a') as fp:
        writer = csv.writer(fp)
        predictors = get_predictors(region)
        covars = ['meantas', 'loggdppc', 'logpopop']
        writer.writerow([region, year, model] + [predictors[covar] for covar in covars])

mode_iterators = {'median': iterate_median, 'montecarlo': iterate_montecarlo, 'single': iterate_single, 'writebins': iterate_writebins, 'writevals': iterate_writevals}

mode = sys.argv[1]
assert mode in mode_iterators.keys()

mod = importlib.import_module("impacts." + module + ".allmodels")

get_model = effectset.get_model_server
do_only = "interpolation"

mod.preload()

for batchdir, pvals, clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel in mode_iterators[mode]():
    print clim_scenario, clim_model
    print econ_scenario, econ_model

    targetdir = os.path.join(outputdir, batchdir, clim_scenario, clim_model, econ_model, econ_scenario)

    if os.path.exists(targetdir):
        continue

    print targetdir
    os.makedirs(targetdir)

    effectset.make_pval_file(targetdir, pvals)
    if mode == 'writebins':
        mod.produce(targetdir, weatherbundle, economicmodel, get_model, pvals, do_only=do_only, do_farmers=False, result_callback=binresult_callback, push_callback=binpush_callback)
    elif mode == 'writevals':
        mod.produce(targetdir, weatherbundle, economicmodel, get_model, pvals, do_only=do_only, do_farmers=False, result_callback=valresult_callback, push_callback=valpush_callback)
    else:
        mod.produce(targetdir, weatherbundle, economicmodel, get_model, pvals, do_only=do_only, do_farmers=False) # Don't do until all else is working

    if mode != 'writebins' and mode != 'writevals':
        # Generate historical baseline
        historybundle = weather.RepeatedHistoricalWeatherBundle.make_historical(weatherbundle, None if mode == 'median' else pvals['histclim'].get_seed())
        pvals.lock()

        mod.produce(targetdir, historybundle, economicmodel, get_model, pvals, country_specific=False, suffix='-histclim', do_only=do_only)

    effectset.make_pval_file(targetdir, pvals)
