"""
Manages rcps and econ and climate models, and generate.effectset.simultaneous_application handles the regions and years.
"""

import os, itertools, importlib, shutil, csv, time, yaml, tempfile
from collections import OrderedDict
import numpy as np
from . import loadmodels
from . import weather, pvalses, timing
from adaptation import curvegen
from interpret import configs
from openest.generate import diagnostic
from impactlab_tools.utils import files, paralog
import cProfile, pstats, io, metacsv

# Top-level configuration (for debugging)
do_single = False

def main(config, runid=None):
    """Main generate func, given run config dict and run ID str for logging

    Parameters
    ----------
    config : MutableMapping
        Run configurations.
    runid : str or None, optional
        Run ID, used for logging and output filenames if `config` is missing
        "module". If `None`, then uses `config["runid"]`. This argument is
        for legacy purposes. Prefer using "runid" in `config`. If `runid` is
        given and "runid" is also in `config` then uses `runid` arg and a 
        warning is printed. This is for backwards compatibility.
    """
    print("Initializing...")

    if runid is None:
        runid = config["runid"]
    elif config.get("runid"):
        # For backwards compatibility, if runid is passed in *and* in config, 
        # then use arg.
        print(f"WARNING: Overriding configuration runid:{config['runid']} with argument runid:{runid}")
        config["runid"] = runid

    # Collect the configuration
    claim_timeout = config.get('timeout', 12) * 60*60
    singledir = config.get('singledir', 'single')

    # Create the object for claiming directories
    statman = paralog.StatusManager('generate', "generate.generate " + str(runid), 'logs', claim_timeout)

    targetdir = None # The current targetdir

    ### Mode-specific iterators, yielding target directories to process

    def iterate_median():
        for clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel in loadmodels.random_order(mod.get_bundle_iterator(config), config):
            pvals = pvalses.ConstantPvals(.5)
            yield 'median', pvals, clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel

    def iterate_montecarlo():
        # How many monte carlo iterations do we do?
        mc_n = config.get('mc-n', config.get('mc_n'))
        if mc_n is None:
            mc_batch_iter = itertools.count()
        else:
            mc_batch_iter = list(range(int(mc_n)))

        # If `only-batch-number` is in run config, overrides `mc_n`.
        only_batch_number = config.get('only-batch-number')
        if only_batch_number is not None:
            mc_batch_iter = [int(only_batch_number)]

        for batch in mc_batch_iter:
            for clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel in loadmodels.random_order(mod.get_bundle_iterator(config), config):
                # Use "pvals" seeds from config, if available.
                if 'pvals' in list(config.keys()):
                    pvals = pvalses.load_pvals(config['pvals'])
                else:
                    # Old default.
                    pvals = pvalses.OnDemandRandomPvals()
                yield 'batch' + str(batch), pvals, clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel

    def iterate_nosideeffects():
        clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel = loadmodels.single(mod.get_bundle_iterator(config))
        pvals = pvalses.ConstantPvals(.5)

        yield None, pvals, clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel

    def iterate_single():
        if 'only-rcp' not in config:
            config['only-rcp'] = loadmodels.single_clim_scenario
        if 'only-models' not in config:
            config['only-models'] = [loadmodels.single_clim_model]
        clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel = loadmodels.single(mod.get_bundle_iterator(config))
        pvals = pvalses.ConstantPvals(.5)

        # Check if this already exists and delete if so
        targetdir = files.configpath(os.path.join(config['outputdir'], singledir, clim_scenario, clim_model, econ_model, econ_scenario))
        if os.path.exists(targetdir) and not config.get('do_fillin', False):
            shutil.rmtree(targetdir)

        yield singledir, pvals, clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel

    ### Callback functions, for recording internal data

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
        elif 'labor' in config['module']:
            covars = ['loggdppc', 'hotdd_30*(tasmax - 27)*I_{T >= 27}', 'colddd_10*(27 - tasmax)*I_{T < 27}']
            covarnames = ['loggdppc', 'hotdd_30', 'colddd_10']
        elif 'energy' in config['module']:
            covars = ['climtas', 'loggdppc']
            covarnames = ['climtas', 'loggdppc']

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
            except Exception as ex:
                print("Exception but returning anyways:")
                print(ex)
                version = module + config['outputdir']

            metacsv.to_header(filepath, attrs=OrderedDict([('oneline', "Yearly covariates by region and year"), ('version', version), ('author', "James R."), ('contact', "jrising@berkeley.edu"), ('dependencies', [model + '.nc4'])]), variables=OrderedDict(variables))
            with open(filepath, 'a') as fp:
                writer = csv.writer(fp)
                writer.writerow(['region', 'year', 'model'] + covarnames)

        with open(filepath, 'a') as fp:
            writer = csv.writer(fp)
            predictors = get_predictors(region)
            writer.writerow([region, year, model] + [predictors[covar] for covar in covars])

    def genericpush_callback(region, year, application, get_predictors, model, weatherbundle=None, economicmodel=None):
        if isinstance(year, np.ndarray):
            year = year.tolist()
        if isinstance(region, np.ndarray):
            region = region.tolist()
        predictors = get_predictors(region)
        for predictor in predictors:
            diagnostic.record(region, year, predictor, predictors[predictor])
        if economicmodel is not None:
            diagnostic.record(region, year, 'population', economicmodel.get_population_year(region, year))

    # Select the iterator based on the mode

    mode_iterators = {'median': iterate_median, 'montecarlo': iterate_montecarlo, 'lincom': iterate_single, 'single': iterate_single, 'writesplines': iterate_single, 'writepolys': iterate_single, 'writecalcs': iterate_single, 'profile': iterate_nosideeffects, 'diagnostic': iterate_nosideeffects}

    assert 'mode' in config, "Configuration does not contain 'mode'."
    assert config['mode'] in list(mode_iterators.keys())

    # Load the module for setting up the calculation

    start = timing.process_time()

    if not config.get('module'):
        # Specification and run config already together.
        mod = importlib.import_module("interpret.container")
        shortmodule = str(runid)
    elif config['module'][-4:] == '.yml':
        # Specification config in another yaml file.
        mod = importlib.import_module("interpret.container")
        with open(config['module'], 'r') as fp:
            config.update(yaml.load(fp))
        shortmodule = os.path.basename(config['module'])[:-4]
    else:
        # Specification config uses old module/script system, module needs to be imported.
        mod = importlib.import_module("impacts." + config['module'] + ".allmodels")
        shortmodule = config['module']

    mod.preload()

    # Loop through target directories

    for batchdir, pvals, clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel in mode_iterators[config['mode']]():
        # Check if we should process this directory
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

        if 'gcm' in config and config['gcm'] != clim_model:
            continue

        print(clim_scenario, clim_model)
        print(econ_scenario, econ_model)

        if config['mode'] == 'profile':
            pr = cProfile.Profile()
            pr.enable()

        # Claim the directory
        if statman.is_claimed(targetdir) and mode_iterators[config['mode']] == iterate_single:
            try:
                paralog.StatusManager.kill_active(targetdir, 'generate') # if do_fillin and crashed, could still exist
            except Exception as ex:
                print("Got exception but passing anyways:")
                print(ex)
                pass
        elif not statman.claim(targetdir) and 'targetdir' not in config:
            continue

        print(targetdir)

        # Load the pvals data, if available
        if pvalses.has_pval_file(targetdir):
            oldpvals = pvalses.read_pval_file(targetdir)
            if oldpvals is not None:
                pvals = oldpvals
        else:
            pvalses.make_pval_file(targetdir, pvals)

        # Produce the results!

        if config['mode'] == 'writesplines':
            mod.produce(targetdir, weatherbundle, economicmodel, pvals, config, push_callback=splinepush_callback, diagnosefile=os.path.join(targetdir, shortmodule + "-allcalcs.csv"))
        elif config['mode'] in ['writepolys', 'lincom']:
            mod.produce(targetdir, weatherbundle, economicmodel, pvals, config, push_callback=polypush_callback, diagnosefile=os.path.join(targetdir, shortmodule + "-allcalcs.csv"))
        elif config['mode'] in ['writecalcs']:
            mod.produce(targetdir, weatherbundle, economicmodel, pvals, config, push_callback=lambda *args: genericpush_callback(*args, weatherbundle=weatherbundle, economicmodel=economicmodel), diagnosefile=os.path.join(targetdir, shortmodule + "-allcalcs.csv"))
        elif config['mode'] == 'profile':
            mod.produce(targetdir, weatherbundle, economicmodel, pvals, config, profile=True)
            pr.disable()

            statman.release(targetdir, "Profiled")

            s = io.StringIO()
            sortby = 'cumulative'
            ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
            ps.print_stats()
            #ps.print_callers(.5, 'sum')
            print(s.getvalue())
            exit()

        else:
            mod.produce(targetdir, weatherbundle, economicmodel, pvals, config)

        # Also produce historical climate results

        if config['mode'] not in ['writesplines', 'writepolys', 'writecalcs', 'diagnostic'] or config.get('do_historical', False):
            # Generate historical baseline
            print("Historical")
            historybundle = weather.HistoricalWeatherBundle.make_historical(weatherbundle, None if config['mode'] == 'median' else pvals['histclim'].get_seed('yearorder'))
            pvals.lock()

            mod.produce(targetdir, historybundle, economicmodel, pvals, config, suffix='-histclim')

        # Clean up

        pvalses.make_pval_file(targetdir, pvals)

        statman.release(targetdir, "Generated")

        os.system("chmod g+rw " + os.path.join(targetdir, "*"))

        print("Process Time:", timing.process_time() - start)

        if do_single:
            break


if __name__ == '__main__':
    # Legacy run from command line.
    import sys
    from pathlib import Path

    run_id = Path(sys.argv[1]).stem
    run_config = configs.standardize(files.get_allargv_config())

    main(run_config, run_id)
