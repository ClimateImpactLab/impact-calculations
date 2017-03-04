import sys, os, itertools, importlib, shutil, csv, time
from collections import OrderedDict
import loadmodels
import weather, effectset, pvalses
from adaptation import curvegen
from helpers import config, files
import cProfile, pstats, StringIO, metacsv

config = config.getConfigDictFromSysArgv()

REDOCHECK_DELAY = 0 #12*60*60
do_single = False

targetdir = None # The current targetdir

def iterate_median():
    for clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel in loadmodels.random_order(mod.get_bundle_iterator()):
        pvals = effectset.ConstantPvals(.5)
        yield 'median', pvals, clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel

def iterate_montecarlo():
    if config.get('redocheck', False):
        # First go through existing batches, even if not ours
        for batchdir in os.listdir(files.configpath(config['outputdir'])):
            if batchdir[:5] == 'batch':
                for clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel in loadmodels.random_order(mod.get_bundle_iterator()):
                    pvals = effectset.OnDemandRandomPvals()
                    yield batchdir, pvals, clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel

    for batch in itertools.count():
        for clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel in loadmodels.random_order(mod.get_bundle_iterator()):
            pvals = effectset.OnDemandRandomPvals()
            yield 'batch' + str(batch), pvals, clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel

def iterate_single():
    clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel = loadmodels.single(mod.get_bundle_iterator())
    pvals = effectset.ConstantPvals(.5)

    # Check if this already exists and delete if so
    targetdir = files.configpath(os.path.join(config['outputdir'], 'single', clim_scenario, clim_model, econ_model, econ_scenario))
    if os.path.exists(targetdir):
        shutil.rmtree(targetdir)

    yield 'single', pvals, clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel

def binresult_callback(region, year, result, calculation, model):
    filepath = os.path.join(targetdir, config['module'] + "-allbins.csv")
    if not os.path.exists(filepath):
        with open(filepath, 'w') as fp:
            writer = csv.writer(fp)
            writer.writerow(['region', 'year', 'model', 'result', 'bin_nInfC_n13C', 'bin_n13C_n8C', 'bin_87C_n3C', 'bin_n3C_2C', 'bin_2C_7C', 'bin_7C_12C', 'bin_12C_17C', 'bin_17C_22C', 'bin_22C_27C', 'bin_27C_32C', 'bin_32C_InfC'])

    with open(filepath, 'a') as fp:
        writer = csv.writer(fp)
        curve = curvegen.region_curves[region].curr_curve
        writer.writerow([region, year, model, result[0]] + list(curve.yy))

def binpush_callback(region, year, application, get_predictors, model):
    filepath = os.path.join(targetdir, config['module'] + "-allpreds.csv")
    if not os.path.exists(filepath):
        with open(filepath, 'w') as fp:
            writer = csv.writer(fp)
            writer.writerow(['region', 'year', 'model', 'meandays_nInfC_n13C', 'meandays_n13C_n8C', 'meandays_87C_n3C', 'meandays_n3C_2C', 'meandays_2C_7C', 'meandays_7C_12C', 'meandays_12C_17C', 'meandays_17C_22C', 'meandays_22C_27C', 'meandays_27C_32C', 'meandays_32C_InfC', 'loggdppc', 'logpopop'])

    with open(filepath, 'a') as fp:
        writer = csv.writer(fp)
        predictors = get_predictors(region)[0]

        bin_limits = [-100, -13, -8, -3, 2, 7, 12, 17, 22, 27, 32, 100]
        bin_names = ['DayNumber-' + str(bin_limits[bb-1]) + '-' + str(bin_limits[bb]) for bb in range(1, len(bin_limits))]
        covars = bin_names + ['loggdppc', 'logpopop']
        if 'age0-4' in predictors:
            covars += ['age0-4', 'age65+']

        writer.writerow([region, year, model] + [predictors[covar] for covar in covars])

def valresult_callback(region, year, result, calculation, model):
    filepath = os.path.join(targetdir, config['module'] + "-allcoeffs.csv")
    if not os.path.exists(filepath):
        metacsv.to_header(filepath, attrs=OrderedDict([('oneline', "Beta coefficients and result values by region and year"), ('version', config['module'] + config['outputdir'][config['outputdir'].rindex('-'):]), ('author', "James R."), ('contact', "jrising@berkeley.edu"), ('dependencies', [model + '.nc4'])]), variables=OrderedDict([('region', "Hierarchy region index"), ('year', "Year of the result"), ('model', "Specification (determined by the CSVV)"), ('result', "Change in minutes worked by individual [minutes]"), ('tasmax', "Coefficient for tasmax [minutes / C]"), ('tasmax2', "Coefficient for tasmax [minutes / C^2]"), ('tasmax3', "Coefficient for tasmax [minutes / C^3]"), ('tasmax4', "Coefficient for tasmax [minutes / C^4]")]))
        with open(filepath, 'a') as fp:
            writer = csv.writer(fp)
            writer.writerow(['region', 'year', 'model', 'result', 'tasmax', 'tasmax2', 'tasmax3', 'tasmax4'])

    with open(filepath, 'a') as fp:
        writer = csv.writer(fp)
        ccs = curvegen.region_curves[region].curr_curve.ccs
        writer.writerow([region, year, model, result[0]] + list(ccs))

def valpush_callback(region, year, application, get_predictors, model):
    covars = ['coldd_agg', 'hotdd_agg', 'loggdppc', 'logpopop']

    filepath = os.path.join(targetdir, config['module'] + "-allpreds.csv")
    if not os.path.exists(filepath):
        metacsv.to_header(filepath, attrs=OrderedDict([('oneline', "Yearly covariates by region and year"), ('version', config['module'] + config['outputdir'][config['outputdir'].rindex('-'):]), ('author', "James R."), ('contact', "jrising@berkeley.edu"), ('dependencies', [model + '.nc4'])]), variables=OrderedDict([('region', "Hierarchy region index"), ('year', "Year of the result"), ('model', "Specification (determined by the CSVV)"), ('coldd_agg', "Degree days below 10 C [C day]"), ('hotdd_agg', "Degree days above 30 C [C day]"), ('loggdppc', "Log GDP per capita [none]"), ('logpopop', "Log population-weighted population density [none]")]))
        with open(filepath, 'a') as fp:
            writer = csv.writer(fp)
            writer.writerow(['region', 'year', 'model'] + covars)

    with open(filepath, 'a') as fp:
        writer = csv.writer(fp)
        predictors = get_predictors(region)
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

    targetdir = files.configpath(os.path.join(config['outputdir'], batchdir, clim_scenario, clim_model, econ_model, econ_scenario))

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
        print "Historical"
        historybundle = weather.RepeatedHistoricalWeatherBundle.make_historical(weatherbundle, None if config['mode'] == 'median' else pvals['histclim'].get_seed())
        pvals.lock()

        mod.produce(targetdir, historybundle, economicmodel, get_model, pvals, country_specific=False, suffix='-histclim', do_only=do_only)

    effectset.make_pval_file(targetdir, pvals)

    if do_single:
        break
