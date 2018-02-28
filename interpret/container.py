## Equivalent to `allmodels.py` for imperics .yml specifications.

import os, glob, copy, warnings
from impactlab_tools.utils import files
from generate import weather, server, effectset, caller, checks
from adaptation import csvvfile
from climate.discover import discover_variable, discover_derived_variable, standard_variable
from interpret import configs

def preload():
    pass

def get_bundle_iterator(config):
    timerate = config.get('timerate', 'day')
    discoverers = []
    for variable in config['climate']:
        discoverers.append(standard_variable(variable, timerate))

    if len(discoverers) == 1:
        return discoverers[0]

    return weather.iterate_bundles(*discoverers, **config)

def check_doit(targetdir, basename, suffix, config, deletebad=False):
    filepath = os.path.join(targetdir, basename + suffix + '.nc4')
    if not os.path.exists(filepath):
        print "REDO: Cannot find", filepath
        return True

    # Check if has 100 valid years
    checkargs = {}
    if 'filter-region' in config:
        checkargs['regioncount'] = 1
    if not checks.check_result_100years(filepath, **checkargs):
        print "REDO: Incomplete", basename, suffix
        if deletebad:
            os.remove(filepath)
        return True

    return False

def get_modules(config):
    models = config['models']
    for model in models:
        csvvs = model['csvvs']
        if 'module' in model:
            module = model['module']
            specconf = model
        elif 'specification' in model:
            module = 'interpret.specification'
            specconf = model['specification']
        elif 'calculation' in model:
            module = 'interpret.calcspec'
            specconf = model
        else:
            assert False, "Model missing one of 'module', 'specification', or 'calculation'."

        yield model, csvvs, module, specconf

def produce(targetdir, weatherbundle, economicmodel, pvals, config, push_callback=None, suffix='', profile=False, diagnosefile=False):
    if push_callback is None:
        push_callback = lambda reg, yr, app, predget, mod: None

    for model, csvvs, module, specconf in get_modules(config):
        if isinstance(csvvs, list):
            for csvv in csvvs:
                for filepath in glob.glob(files.sharedpath(csvv)):
                    basename = os.path.basename(filepath)[:-5]
                    produce_csvv(basename, filepath, module, specconf, targetdir, weatherbundle, economicmodel, pvals, configs.merge(config, model), push_callback, suffix, profile, diagnosefile)
                    if profile:
                        return
        else:
            filepaths = glob.glob(files.sharedpath(csvvs))
            if not filepaths:
                warnings.warn("Cannot find any files that match %s" % files.sharedpath(csvvs))
                
            for filepath in filepaths:
                basename = os.path.basename(filepath)[:-5]
                produce_csvv(basename, filepath, module, specconf, targetdir, weatherbundle, economicmodel, pvals, configs.merge(config, model), push_callback, suffix, profile, diagnosefile)
                if profile:
                    return

def produce_csvv(basename, csvv, module, specconf, targetdir, weatherbundle, economicmodel, pvals, config, push_callback, suffix, profile, diagnosefile):
    if specconf.get('csvv-organization', 'normal') == 'three-ages':
        print "Splitting into three ages."
        specconf_age = copy.copy(specconf)
        specconf_age['csvv-organization'] = 'normal'
        csvv = csvvfile.read(csvv)
        produce_csvv(basename + '-young', csvvfile.subset(csvv, slice(0, len(csvv['gamma']) / 3)), module, specconf_age,
                     targetdir, weatherbundle, economicmodel, pvals, config, push_callback, suffix, profile, diagnosefile)
        produce_csvv(basename + '-older', csvvfile.subset(csvv, slice(len(csvv['gamma']) / 3, 2 * len(csvv['gamma']) / 3)), module, specconf_age,
                     targetdir, weatherbundle, economicmodel, pvals, config, push_callback, suffix, profile, diagnosefile)
        produce_csvv(basename + '-oldest', csvvfile.subset(csvv, slice(2 * len(csvv['gamma']) / 3, len(csvv['gamma']))), module, specconf_age,
                     targetdir, weatherbundle, economicmodel, pvals, config, push_callback, suffix, profile, diagnosefile)
        return

    # Full Adaptation
    if check_doit(targetdir, basename, suffix, config):
        print "Full Adaptation"
        calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(csvv, module, weatherbundle, economicmodel, pvals[basename], specconf=specconf, config=config, standard=False)

        effectset.generate(targetdir, basename + suffix, weatherbundle, calculation, specconf['description'] + ", with interpolation and adaptation through interpolation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, push_callback=lambda reg, yr, app: push_callback(reg, yr, app, baseline_get_predictors, basename), diagnosefile=diagnosefile.replace('.csv', '-' + basename + '.csv') if diagnosefile else False)

        if profile:
            return
        
        if config.get('do_farmers', False) and not weatherbundle.is_historical():
            # Lock in the values
            pvals[basename].lock()

            if check_doit(targetdir, basename + "-noadapt", suffix, config):
                print "No adaptation"
                calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(csvv, module, weatherbundle, economicmodel, pvals[basename], specconf=specconf, farmer='noadapt', config=config, standard=False)
                effectset.generate(targetdir, basename + "-noadapt" + suffix, weatherbundle, calculation, specconf['description'] + ", with no adaptation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, push_callback=lambda reg, yr, app: push_callback(reg, yr, app, baseline_get_predictors, basename))

            if check_doit(targetdir, basename + "-incadapt", suffix, config):
                print "Income-only adaptation"
                calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(csvv, module, weatherbundle, economicmodel, pvals[basename], specconf=specconf, farmer='incadapt', config=config, standard=False)
                effectset.generate(targetdir, basename + "-incadapt" + suffix, weatherbundle, calculation, specconf['description'] + ", with interpolation and only environmental adaptation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, push_callback=lambda reg, yr, app: push_callback(reg, yr, app, baseline_get_predictors, basename))
