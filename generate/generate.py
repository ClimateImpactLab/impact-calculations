import sys, os, itertools, importlib, shutil
import loadmodels
import weather, effectset

outputdir = sys.argv[3]

def iterate_median():
    for clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel in loadmodels.random_order(mod.climatebasedir, mod.readercls):
        pvals = effectset.ConstantPvals(.5)
        yield 'median', pvals, clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel

def iterate_montecarlo():
    for batch in itertools.count():
        for clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel in loadmodels.random_order(mod.climatebasedir, mod.readercls):
            pvals = effectset.OnDemandRandomPvals()
            yield 'batch' + str(batch), pvals, clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel

def iterate_single():
    clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel = loadmodels.single(mod.climatebasedir, mod.readercls)
    pvals = effectset.ConstantPvals(.5)

    # Check if this already exists and delete if so
    targetdir = os.path.join(outputdir, 'single', clim_scenario, clim_model, econ_model, econ_scenario)
    if os.path.exists(targetdir):
        shutil.rmtree(targetdir)

    yield 'single', pvals, clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel

mode_iterators = {'median': iterate_median, 'montecarlo': iterate_montecarlo, 'single': iterate_single}

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
    mod.produce(targetdir, weatherbundle, economicmodel, get_model, pvals, do_only=do_only, do_farmers=True)

    # Generate historical baseline
    historybundle = weather.RepeatedHistoricalWeatherBundle.make_historical(weatherbundle, None if mode == 'median' else pvals['histclim'].get_seed())
    pvals.lock()

    effectset.make_pval_file(targetdir, pvals)

    mod.produce(targetdir, historybundle, economicmodel, get_model, pvals, country_specific=False, suffix='-histclim', do_only=do_only)
