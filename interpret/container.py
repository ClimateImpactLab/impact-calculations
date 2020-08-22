## Equivalent to `allmodels.py` for imperics .yml specifications.

import copy
import glob
import os
import warnings
from functools import partial

from impactlab_tools.utils import files

from adaptation import csvvfile
from climate.discover import standard_variable
from generate import weather, effectset, caller, checks
from interpret import configs


def preload():
    pass

def get_bundle_iterator(config):
    if 'timerate' not in config:
        print("Warning: 'timerate' not found in the configuration; assuming daily.")
    timerate = config.get('timerate', 'day')
    discoverers = []
    for variable in config['climate']:
        discoverers.append(standard_variable(variable, timerate, **config))

    return weather.iterate_bundles(*discoverers, **config)

def check_doit(targetdir, basename, suffix, config, deletebad=False):
    filepath = os.path.join(targetdir, basename + suffix + '.nc4')
    if not os.path.exists(filepath):
        print("REDO: Cannot find", filepath)
        return True

    # Check if has 100 valid years
    checkargs = {}
    if 'filter-region' in config:
        checkargs['regioncount'] = 1
    if not checks.check_result_100years(filepath, **checkargs):
        print("REDO: Incomplete", basename, suffix)
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

def get_modules_csvv(config):
    for model, csvvs, module, specconf in get_modules(config):
        if isinstance(csvvs, list):
            for csvv in csvvs:
                for filepath in glob.glob(files.configpath(csvv)):
                    yield model, filepath, module, specconf
        else:
            filepaths = glob.glob(files.configpath(csvvs))
            if not filepaths:
                warnings.warn("Cannot find any files that match %s" % files.configpath(csvvs))
                
            for filepath in filepaths:
                yield model, filepath, module, specconf

def produce(targetdir, weatherbundle, economicmodel, pvals, config, push_callback=None, suffix='', profile=False, diagnosefile=False):
    if push_callback is None:
        push_callback = lambda reg, yr, app, predget, mod: None

    for model, csvvpath, module, specconf in get_modules_csvv(config):
        basename = os.path.basename(csvvpath)[:-5]
        produce_csvv(basename, csvvpath, module, specconf, targetdir, weatherbundle, economicmodel, pvals, configs.merge(config, model), push_callback, suffix, profile, diagnosefile)
        if profile:
            return

def csvv_organization(specconf):
    """Interpret the `csvv-organization` option in the configuration to split a CSVV up into pieces."""
    if specconf.get('csvv-organization', 'normal') == 'three-ages':
        print("Splitting into three ages.")
        return ["young", "older", "oldest"]
    elif specconf.get('csvv-organization', 'normal') == 'lowhigh':
        print("Splitting into two risk groups.")
        return ["lowrisk", "highrisk"]
    else:
        return None


def _projection(targetdir, basename, suffix, config, csvv, module,
                weatherbundle, economicmodel, pvals, specconf, push_callback,
                deltamethod_vcv, diagnosefile=None, strategy='full'):
    """Trigger projection with adaptation scenario

    This is purely syntactic sugar to condense some crap. It's where
    we deal with logic about input and configurations different adaption
    scenarios.
    """
    opts = {
        'full': ('Full Adaptation', 'with interpolation and adaptation through interpolation', ''),
        'incadapt': ('Income-only adaptation', 'with no adaptation', '-incadapt'),
        'noadapt': ('No adaptation', 'with interpolation and only environmental adaptation', '-noadapt'),
    }
    fullname, explanation, fileflag = opts[strategy]

    if diagnosefile:
        diagnosefile = diagnosefile.replace('.csv', '-' + basename + '.csv')

    if check_doit(targetdir, f'{basename}{fileflag}', suffix, config):
        print(fullname)
        calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(csvv, module, weatherbundle,
                                                                                        economicmodel, pvals[basename],
                                                                                        specconf=specconf,
                                                                                        farmer=strategy,
                                                                                        config=config,
                                                                                        standard=False)
        effectset.generate(targetdir, f'{basename}{fileflag}{suffix}', weatherbundle, calculation,
                           f"{specconf['description']}, {explanation}.",
                           dependencies + weatherbundle.dependencies + economicmodel.dependencies, config,
                           push_callback=lambda reg, yr, app: push_callback(reg, yr, app, baseline_get_predictors,
                                                                            basename),
                           diagnosefile=diagnosefile,
                           deltamethod_vcv=deltamethod_vcv)


def produce_csvv(basename, csvv, module, specconf, targetdir, weatherbundle, economicmodel, pvals, config, push_callback, suffix, profile, diagnosefile):
    csvv_parts = csvv_organization(specconf)
    if csvv_parts is not None:
        specconf_part = copy.copy(specconf)
        specconf_part['csvv-organization'] = 'normal'
        csvv = csvvfile.read(csvv)
        n_csvv = len(csvv['gamma'])
        n_parts = len(csvv_parts)
        for partii in range(n_parts):
            produce_csvv(basename + '-' + csvv_parts[partii],
                         csvvfile.subset(csvv, slice(int(partii * n_csvv / n_parts), int((partii + 1) * n_csvv / n_parts))),
                         module, specconf_part, targetdir, weatherbundle, economicmodel, pvals, config, push_callback, suffix,
                         profile, diagnosefile)
        return

    deltamethod_vcv = False
    if config.get('deltamethod', False):
        if isinstance(csvv, str):
            csvv = csvvfile.read(csvv)
        deltamethod_vcv = csvv['gammavcv']

    if diagnosefile:
        diagnosefile = diagnosefile.replace('.csv', '-' + basename + '.csv')

    # So don't repeat big arg pass over and over...
    adapt_projection = partial(_projection, targetdir, basename,
                               suffix, config, csvv, module, weatherbundle,
                               economicmodel, pvals, specconf, push_callback,
                               deltamethod_vcv)

    only_adapt = config.get('only-adapt') or config.get('adapt')
    if only_adapt:
        adapt_projection(strategy=only_adapt, diagnosefile=diagnosefile)
    else:
        adapt_projection(
            strategy='full',
            diagnosefile=diagnosefile,
        )

        if profile:
            return

        if config.get('do_farmers', False) and (not weatherbundle.is_historical() or config['do_farmers'] == 'always'):
            # Lock in the values
            pvals[basename].lock()
            adapt_projection(strategy='noadapt')
            adapt_projection(strategy='incadapt')
