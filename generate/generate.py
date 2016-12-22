import sys, os, itertools, importlib, shutil, csv, time
import loadmodels
import weather, effectset, pvalses
from adaptation import adapting_curve, curvegenv2
from helpers import config
import cProfile, pstats, StringIO

config = config.getConfigDictFromSysArgv()

REDOCHECK_DELAY = 12*60*60

targetdir = None # The current targetdir

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
    targetdir = os.path.join(config['outputdir'], 'single-new', clim_scenario, clim_model, econ_model, econ_scenario)
    if os.path.exists(targetdir):
        shutil.rmtree(targetdir)

    yield 'single-new', pvals, clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel

def binresult_callback(region, year, result, calculation, model):
    filepath = os.path.join(targetdir, config['module'] + "-allbins.csv")
    if not os.path.exists(filepath):
        with open(filepath, 'w') as fp:
            writer = csv.writer(fp)
            writer.writerow(['region', 'year', 'model', 'result', 'bin_nInfC_n17C', 'bin_n17C_n12C', 'bin_n12C_n7C', 'bin_n7C_n2C', 'bin_n2C_3C', 'bin_3C_8C', 'bin_8C_13C', 'bin_13C_18C', 'bin_18C_23C', 'bin_23C_28C', 'bin_28C_33C', 'bin_33C_InfC'])

    with open(filepath, 'a') as fp:
        writer = csv.writer(fp)
        curve = adapting_curve.region_stepcurves[region].curr_curve
        writer.writerow([region, year, model, result[0]] + list(curve.yy))

def binpush_callback(region, year, application, get_predictors, model):
    filepath = os.path.join(targetdir, config['module'] + "-allpreds.csv")
    if not os.path.exists(filepath):
        with open(filepath, 'w') as fp:
            writer = csv.writer(fp)
            writer.writerow(['region', 'year', 'model', 'meandays_nInfC_n17C', 'meandays_n17C_n12C', 'meandays_n12C_n7C', 'meandays_n7C_n2C', 'meandays_n2C_3C', 'meandays_3C_8C', 'meandays_8C_13C', 'meandays_13C_18C', 'meandays_18C_23C', 'meandays_23C_28C', 'meandays_28C_33C', 'meandays_33C_InfC', 'log gdppc', 'log popop', 'age0-4', 'age65+'])

    with open(filepath, 'a') as fp:
        writer = csv.writer(fp)
        predictors = get_predictors(region)[0]

        bin_limits = [-100, -17, -12, -7, -2, 3, 8, 13, 18, 23, 28, 33, 100]
        bin_names = ['DayNumber-' + str(bin_limits[bb-1]) + '-' + str(bin_limits[bb]) for bb in range(1, len(bin_limits))]
        covars = bin_names + ['loggdppc', 'logpopop']
        if 'age0-4' in predictors:
            covars += ['age0-4', 'age65+']

        writer.writerow([region, year, model] + [predictors[covar] for covar in covars])

def valresult_callback(region, year, result, calculation, model):
    filepath = os.path.join(targetdir, config['module'] + "-allcoeffs.csv")
    if not os.path.exists(filepath):
        with open(filepath, 'w') as fp:
            writer = csv.writer(fp)
            writer.writerow(['region', 'year', 'model', 'result', 'tasmax', 'tasmax2', 'tasmax3', 'tasmax4'])

    with open(filepath, 'a') as fp:
        writer = csv.writer(fp)
        ccs = curvegenv2.region_polycurves[region].curr_curve.ccs
        writer.writerow([region, year, model, result[0]] + list(ccs))

def valpush_callback(region, year, application, get_predictors, model):
    filepath = os.path.join(targetdir, config['module'] + "-allpreds.csv")
    if not os.path.exists(filepath):
        with open(filepath, 'w') as fp:
            writer = csv.writer(fp)
            writer.writerow(['region', 'year', 'model', 'meantas', 'log gdppc', 'log popop'])

    with open(filepath, 'a') as fp:
        writer = csv.writer(fp)
        predictors = get_predictors(region)
        covars = ['tasmax', 'loggdppc', 'logpopop']
        writer.writerow([region, year, model] + [predictors[covar] for covar in covars])

mode_iterators = {'median': iterate_median, 'montecarlo': iterate_montecarlo, 'single': iterate_single, 'writebins': iterate_single, 'writevals': iterate_single, 'profile': iterate_single}

assert config['mode'] in mode_iterators.keys()

mod = importlib.import_module("impacts." + config['module'] + ".allmodels")

get_model = effectset.get_model_server
do_only = "interpolation"

mod.preload()

for batchdir, pvals, clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel in mode_iterators[config['mode']]():
    print clim_scenario, clim_model
    print econ_scenario, econ_model

    if config['mode'] == 'profile':
        pr = cProfile.Profile()
        pr.enable()

    targetdir = os.path.join(config['outputdir'], batchdir, clim_scenario, clim_model, econ_model, econ_scenario)

    if config.get('redocheck', False):
        if os.path.exists(targetdir) and os.path.exists(os.path.join(targetdir, config['redocheck'])):
            continue

        if pvalses.has_pval_file(targetdir) and time.time() - os.path.getmtime(pvalses.get_pval_file(targetdir)) < REDOCHECK_DELAY:
            continue
    else:
        if os.path.exists(targetdir) and pvalses.has_pval_file(targetdir):
            continue

    print targetdir
    if not os.path.exists(targetdir):
        os.makedirs(targetdir)

    if config.get('redocheck', False) and effectset.has_pval_file(targetdir):
        pvals = effectset.read_pval_file(targetdir)
        with open(os.path.join(targetdir, config['redocheck']), 'w') as fp:
            fp.write("Check.")
    else:
        effectset.make_pval_file(targetdir, pvals)

    if config['mode'] == 'writebins':
        mod.produce(targetdir, weatherbundle, economicmodel, get_model, pvals, do_only=do_only, do_farmers=False, result_callback=binresult_callback, push_callback=binpush_callback, redocheck=config.get('redocheck', False), diagnosefile=os.path.join(targetdir, config['module'] + "-allcalcs.csv"))
    elif config['mode'] == 'writevals':
        mod.produce(targetdir, weatherbundle, economicmodel, get_model, pvals, do_only=do_only, do_farmers=False, result_callback=valresult_callback, push_callback=valpush_callback, redocheck=config.get('redocheck', False), diagnosefile=os.path.join(targetdir, config['module'] + "-allcalcs.csv"))
    elif config['mode'] == 'profile':
        mod.produce(targetdir, weatherbundle, economicmodel, get_model, pvals, do_only=do_only, profile=True, redocheck=config.get('redocheck', False))
        pr.disable()

        s = StringIO.StringIO()
        sortby = 'cumulative'
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        #ps.print_callers(.5, 'sum')
        print s.getvalue()
        exit()

    else:
        mod.produce(targetdir, weatherbundle, economicmodel, get_model, pvals, do_only=do_only, do_farmers=True, redocheck=config.get('redocheck', False))

    if config['mode'] != 'writebins' and config['mode'] != 'writevals':
        # Generate historical baseline
        historybundle = weather.RepeatedHistoricalWeatherBundle.make_historical(weatherbundle, None if config['mode'] == 'median' else pvals['histclim'].get_seed())
        pvals.lock()

        mod.produce(targetdir, historybundle, economicmodel, get_model, pvals, country_specific=False, suffix='-histclim', do_only=do_only)

    effectset.make_pval_file(targetdir, pvals)
