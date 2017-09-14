"""
Manages rcps and econ and climate models, and generate.effectset.simultaneous_application handles the regions and years.
"""

import sys, os, itertools, importlib, shutil, csv, time, yaml, tempfile
from collections import OrderedDict
import loadmodels
import weather, pvalses, timing
from adaptation import curvegen
from impactlab_tools.utils import files, paralog
import cProfile, pstats, StringIO, metacsv

config = files.get_allargv_config()

CLAIM_TIMEOUT = 12*60*60
do_single = False

singledir = config.get('singledir', 'single')

statman = paralog.StatusManager('generate', "generate.generate " + sys.argv[1], 'logs', CLAIM_TIMEOUT)

targetdir = None # The current targetdir

def iterate_median():
    for clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel in loadmodels.random_order(mod.get_bundle_iterator(config)):
        pvals = pvalses.ConstantPvals(.5)
        yield 'median', pvals, clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel

def iterate_montecarlo():
    for batch in itertools.count():
        for clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel in loadmodels.random_order(mod.get_bundle_iterator(config)):
            pvals = pvalses.OnDemandRandomPvals()
            yield 'batch' + str(batch), pvals, clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel

def iterate_nosideeffects():
    clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel = loadmodels.single(mod.get_bundle_iterator(config))
    pvals = pvalses.ConstantPvals(.5)

    yield None, pvals, clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel

def iterate_single():
    clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel = loadmodels.single(mod.get_bundle_iterator(config))
    pvals = pvalses.ConstantPvals(.5)

    # Check if this already exists and delete if so
    targetdir = files.configpath(os.path.join(config['outputdir'], singledir, clim_scenario, clim_model, econ_model, econ_scenario))
    if os.path.exists(targetdir):
        shutil.rmtree(targetdir)

    yield singledir, pvals, clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel

def splinepush_callback(region, year, application, get_predictors, model):
    if 'mortality' in config['module']:
        covars = ['climtas', 'loggdppc', 'logpopop']
    else:
        covars = ['loggdppc', 'hotdd_30*(tasmax - 27)*I_{T >= 27}', 'colddd_10*(27 - tasmax)*I_{T < 27}']

    module = config['module']
    if module[-4:] == '.yml':
        module = os.path.basename(module)[:-4]
        
    filepath = os.path.join(targetdir, module + "-allpreds.csv")
    if not os.path.exists(filepath):
        metacsv.to_header(filepath, attrs=OrderedDict([('oneline', "Yearly covariates by region and year"), ('version', module + config['outputdir'][config['outputdir'].rindex('-'):]), ('author', "James R."), ('contact', "jrising@berkeley.edu"), ('dependencies', [model + '.nc4'])]), variables=OrderedDict([('region', "Hierarchy region index"), ('year', "Year of the result"), ('model', "Specification (determined by the CSVV)"), ('climtas', "Average surface temperature [C]"), ('loggdppc', "Log GDP per capita [none]"), ('logpopop', "Log population-weighted population density [none]")]))
        with open(filepath, 'a') as fp:
            writer = csv.writer(fp)
            writer.writerow(['region', 'year', 'model'] + covars)

    with open(filepath, 'a') as fp:
        writer = csv.writer(fp)
        predictors = get_predictors(region)

        writer.writerow([region, year, model] + [predictors[covar] for covar in covars])

def polypush_callback(region, year, application, get_predictors, model):
    if 'mortality' in config['module']:
        covars = ['climtas', 'loggdppc']
        covarnames = ['climtas', 'loggdppc']
    else:
        covars = ['loggdppc', 'hotdd_30*(tasmax - 27)*I_{T >= 27}', 'colddd_10*(27 - tasmax)*I_{T < 27}']
        covarnames = ['loggdppc', 'hotdd_30', 'colddd_10']

    module = config['module']
    if '.yml' in module:
        module = os.path.basename(module)[:-4]
        
    filepath = os.path.join(targetdir, module + "-allpreds.csv")
    if not os.path.exists(filepath):
        vardefs = yaml.load(open(files.configpath("social/variables.yml"), 'r'))
        variables = [('region', "Hierarchy region index"), ('year', "Year of the result"), ('model', "Specification (determined by the CSVV)")]
        for covar in covars:
            if covar in vardefs:
                variables.append((covar, vardefs[covar]))
            else:
                variables.append((covar, "Unknown variable; append social/variables.yml"))

        try:
            version = module + config['outputdir'][config['outputdir'].rindex('-'):]
        except:
            version = module + config['outputdir']
            
        metacsv.to_header(filepath, attrs=OrderedDict([('oneline', "Yearly covariates by region and year"), ('version', version), ('author', "James R."), ('contact', "jrising@berkeley.edu"), ('dependencies', [model + '.nc4'])]), variables=OrderedDict(variables))
        with open(filepath, 'a') as fp:
            writer = csv.writer(fp)
            writer.writerow(['region', 'year', 'model'] + covarnames)

    with open(filepath, 'a') as fp:
        writer = csv.writer(fp)
        predictors = get_predictors(region)
        writer.writerow([region, year, model] + [predictors[covar] for covar in covars])

mode_iterators = {'median': iterate_median, 'montecarlo': iterate_montecarlo, 'lincom': iterate_single, 'single': iterate_single, 'writesplines': iterate_single, 'writepolys': iterate_single, 'profile': iterate_nosideeffects, 'diagnostic': iterate_nosideeffects}

assert config['mode'] in mode_iterators.keys()

start = timing.process_time()

if config['module'][-4:] == '.yml':
    mod = importlib.import_module("interpret.container")
    with open(config['module'], 'r') as fp:
        config.update(yaml.load(fp))
    shortmodule = os.path.basename(config['module'])[:-4]
else:
    mod = importlib.import_module("impacts." + config['module'] + ".allmodels")
    shortmodule = config['module']

mod.preload()

for batchdir, pvals, clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel in mode_iterators[config['mode']]():
    if batchdir is not None:
        targetdir = files.configpath(os.path.join(config['outputdir'], batchdir, clim_scenario, clim_model, econ_model, econ_scenario))

        if 'targetdir' in config:
            if config['targetdir'][-1] == '/' and targetdir[-1] != '/':
                if targetdir + '/' != config['targetdir']:
                    continue
            else:
                if targetdir != config['targetdir']:
                    continue
    
        if config.get('do_fillin', False) and not os.path.exists(targetdir):
            continue
    else:
        targetdir = tempfile.mkdtemp()

    if 'only_gcm' in config and config['only_gcm'] != clim_model:
        continue

    print clim_scenario, clim_model
    print econ_scenario, econ_model

    if config['mode'] == 'profile':
        pr = cProfile.Profile()
        pr.enable()

    if not statman.claim(targetdir) and 'targetdir' not in config:
        continue

    print targetdir

    if pvalses.has_pval_file(targetdir):
        pvals = pvalses.read_pval_file(targetdir)
    else:
        pvalses.make_pval_file(targetdir, pvals)

    if config['mode'] == 'writesplines':
        mod.produce(targetdir, weatherbundle, economicmodel, pvals, config, push_callback=splinepush_callback, diagnosefile=os.path.join(targetdir, shortmodule + "-allcalcs.csv"))
    elif config['mode'] in ['writepolys', 'lincom']:
        mod.produce(targetdir, weatherbundle, economicmodel, pvals, config, push_callback=polypush_callback, diagnosefile=os.path.join(targetdir, shortmodule + "-allcalcs.csv"))
    elif config['mode'] == 'profile':
        mod.produce(targetdir, weatherbundle, economicmodel, pvals, config, profile=True)
        pr.disable()

        statman.release(targetdir, "Profiled")

        s = StringIO.StringIO()
        sortby = 'cumulative'
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        #ps.print_callers(.5, 'sum')
        print s.getvalue()
        exit()

    else:
        mod.produce(targetdir, weatherbundle, economicmodel, pvals, config)

    if config['mode'] not in ['writesplines', 'writepolys', 'diagnostic']:
        # Generate historical baseline
        print "Historical"
        historybundle = weather.HistoricalWeatherBundle.make_historical(weatherbundle, None if config['mode'] == 'median' else pvals['histclim'].get_seed())
        pvals.lock()

        mod.produce(targetdir, historybundle, economicmodel, pvals, config, suffix='-histclim')

    pvalses.make_pval_file(targetdir, pvals)

    statman.release(targetdir, "Generated")

    os.system("chmod g+rw " + os.path.join(targetdir, "*"))

    print "Process Time:", timing.process_time() - start
    
    if do_single:
        break
