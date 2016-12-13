import sys, os, itertools, importlib, shutil
import loadmodels
import weather, effectset

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

def iterate_writebin():
    with open("allbins.csv", 'w') as fp:
        writer = csv.writer(fp)
        writer.writerow(['region', 'year', 'model', 'result', 'bin_nInfC_n17C', 'bin_n17C_n12C', 'bin_n12C_n7C', 'bin_n7C_n2C', 'bin_n2C_3C', 'bin_3C_8C', 'bin_8C_13C', 'bin_13C_18C', 'bin_18C_23C', 'bin_23C_28C', 'bin_28C_33C', 'bin_33C_InfC'])

    with open("allpreds.csv", 'w') as fp:
        writer = csv.writer(fp)
        writer.writerow(['region', 'year', 'meandays_nInfC_n17C', 'meandays_n17C_n12C', 'meandays_n12C_n7C', 'meandays_n7C_n2C', 'meandays_n2C_3C', 'meandays_3C_8C', 'meandays_8C_13C', 'meandays_13C_18C', 'meandays_23C_28C', 'meandays_28C_33C', 'meandays_33C_InfC', 'log gdppc', 'log popop'])

    for allvals in iterate_single():
        yield allvals

def result_callback(region, year, result, calculation, model):
    with open("allbins.csv", 'a') as fp:
        writer = csv.writer(fp)
        curve = adapting_curve.region_stepcurves[region].curr_curve
        writer.writerow([region, year, model, result[0]] + list(curve.yy))

def push_callback(region, year, application, get_predictors):
    with open("allpreds.csv", 'a') as fp:
        writer = csv.writer(fp)
        predictors = get_predictors(region)
        writer.writerow([region, year] + list(predictors[0]))


mode_iterators = {'median': iterate_median, 'montecarlo': iterate_montecarlo, 'single': iterate_single, 'writebin': iterate_writebin}

mode = sys.argv[1]
assert mode in mode_iterators.keys()

module = sys.argv[2]
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
        mod.produce(targetdir, weatherbundle, economicmodel, get_model, pvals, do_only=do_only, do_farmers=False, result_callback=result_callback, push_callback=push_callback)
    else:
        mod.produce(targetdir, weatherbundle, economicmodel, get_model, pvals, do_only=do_only, do_farmers=True)
        
    # Generate historical baseline
    historybundle = weather.RepeatedHistoricalWeatherBundle.make_historical(weatherbundle, None if mode == 'median' else pvals['histclim'].get_seed())
    pvals.lock()

    effectset.make_pval_file(targetdir, pvals)

    mod.produce(targetdir, historybundle, economicmodel, get_model, pvals, country_specific=False, suffix='-histclim', do_only=do_only)
