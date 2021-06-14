import yaml, copy, itertools, importlib, os
from pathlib import Path
from impactlab_tools.utils.files import get_file_config

global_statman = None

def get_config_module(config, config_name):
    """Interpret the `module` entry in a config. Currently also handles `module` as `import`.

    This modifies `config` if the deprecated `module` option pointing
    to an importalbe config is used.

    Parameters
    ----------
    config : dict
	Projection run configuration, with or without an "module" key

    Returns
    -------
    module
        The module used to handle projections.
    str
        A name associated with the configuration.
    """
    if not config.get('module'):
        # Specification and run config already together.
        if config.get('threads', 1) == 1:
            mod = importlib.import_module("interpret.container")
        else:
            mod = importlib.import_module("interpret.parallel_container")
        shortmodule = str(config_name)
    elif os.path.splitext(config['module'])[1] in ['.yml', '.yaml']:
        # Specification config in another yaml file.
        import warnings
        warnings.warn(
            "Pointing 'module:' to YAML files is deprecated, please use 'import:'",
            FutureWarning,
        )
        if config.get('threads', 1) == 1:
            mod = importlib.import_module("interpret.container")
        else:
            mod = importlib.import_module("interpret.parallel_container")

        with open(config['module'], 'r') as fp:
            config.update(yaml.load(fp))
        shortmodule = os.path.basename(config['module'])[:-4]
    else:
        # Specification config uses old module/script system, module needs to be imported.
        mod = importlib.import_module("impacts." + config['module'] + ".allmodels")
        shortmodule = config['module']

    return mod, shortmodule

def merge_import_config(config, fpath):

    """Parse "import" in `config` dict and merge

    Values in 'config' override values from any imported dict.

    Parameters
    ----------
    config : dict
        Projection run configuration, with or without an "import" key pointing
        to a relative or absolute file path.
    fpath : str or pathlib.Path
        Path from which to interpret "import"s in `config`. If `config` is from
        a file on disk, it is usually the absolute path to the directory
        containing this file. Only used if "import" has no root, i.e. no
        prepended "/".

    Returns
    -------
    dict
        Shallow copy of`config` is returned if it contains no "import" key.
        Otherwise, get shallow-copied merge with imported config.
    """
    try:
        import_path = Path(config.pop("import"))
    except KeyError:
        # Nothing to import
        return {**config}

    # Read "import" - relative to fpath, if needed.
    if not import_path.is_absolute():
        if isinstance(fpath, str):
            fpath = Path(fpath)
        import_path = fpath.joinpath(import_path)

    import_config = merge_import_config(
        get_file_config(import_path),
        import_path.parent
    )

    return {**import_config, **config}

def standardize(config):
    newconfig = copy.copy(config)

    for key in config:
        asdash = key.replace('_', '-')
        asscore = key.replace('-', '_')
        if '-' in key and asscore not in config:
            newconfig[asscore] = config[key]
        if '_' in key and asdash not in config:
            newconfig[asdash] = config[key]
                
    return newconfig

def merge(parent, child):
    if isinstance(child, dict):
        result = copy.copy(parent)
        result.update(child)
        return result

    if child not in parent:
        return parent

    result = copy.copy(parent)
    result.update(parent[child])
    return result

def search(config, needle, pathroot=''):
    found = {}
    for key in config:
        if needle == key:
            found[pathroot] = config[key]
        elif isinstance(config[key], dict):
            found.update(search(config[key], needle, pathroot=pathroot + '/' + key))
        elif isinstance(config[key], list):
            found.update(search_list(config[key], needle, pathroot=pathroot + '/' + key))

    return found

def search_list(conflist, needle, pathroot=''):
    found = {}
    for ii in range(len(conflist)):
        if isinstance(conflist[ii], dict):
            found.update(search(conflist[ii], needle, pathroot=pathroot + '/' + str(ii)))
        elif isinstance(conflist[ii], list):
            found.update(search_list(conflist[ii], needle, pathroot=pathroot + '/' + str(ii)))

    return found

def deepcopy(config):
    return copy.deepcopy(config)

def get_batch_iter(config):
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

    return mc_batch_iter

def claim_targetdir(statman, targetdir, is_single, config):
    if statman.is_claimed(targetdir) and is_single:
        try:
            paralog.StatusManager.kill_active(targetdir, 'generate') # if do_fillin and crashed, could still exist
        except Exception as ex:
            print("Got exception but passing anyways:")
            print(ex)
            pass
        return True
    elif not statman.claim(targetdir) and 'targetdir' not in config:
        return False
    return True

def get_regions(allregions, filter_region):
    if filter_region is None:
        my_regions = allregions
    else:
        my_regions = []
        for ii in range(len(allregions)):
            if isinstance(filter_region, str):
                if filter_region in allregions[ii]:
                    my_regions.append(allregions[ii])
            else:
                if filter_region(allregions[ii]):
                    my_regions.append(allregions[ii])
        assert my_regions != [], "No regions remain after filter."

    return my_regions

def get_covariate_rate(config, group):
    """ 
    handles the 'scale-covariate-changes' key and the legacy key 'slowadapt'

    Parameters
    ----------
    config : dict
        projection run configuration
    group : str
        one of 'income' or 'climate'
   
    Returns
    ------- 
    float
        the change in rate for the given covariate group, or 1 for no rate change
    """ 
    if 'scale-covariate-changes' in config and 'slowadapt' in config:
        raise ValueError('the slowadapt and scale-covariate-changes entries of the config file are redundant. Please select either.')
    elif 'slowadapt' in config:
        covar = config.get('slowadapt')
        if covar not in ['climate', 'income', 'both']:
            raise ValueError('the slowadapt entry of the config should be one of "income", "climate", "both"')
        if covar == 'both' or covar == group:
            return .5
        else:
            return 1
    elif 'scale-covariate-changes' in config:
        changes = config.get('scale-covariate-changes')
        if not isinstance(changes, dict):
            raise ValueError('the scale-covariate-changes entry of the config should be a dictionary')
        rate = changes.get(group, 1)
        if rate < 0:
            raise ValueError('all scalars in scale-covariate-changes should be strictly positive floats')
        return rate
    else:
        return 1

