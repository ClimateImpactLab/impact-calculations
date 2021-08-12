import yaml, copy, itertools, importlib, os
from pathlib import Path
from impactlab_tools.utils.files import get_file_config
from collections.abc import MutableMapping, MutableSequence

global_statman = None

def get_config_module(config, config_name):
    """Interpret the `module` entry in a config. Currently also handles `module` as `import`.

    This modifies `config` if the deprecated `module` option pointing
    to an importable config is used.

    Parameters
    ----------
    config : dict
        Projection run configuration, with or without a "module" key.
    config_name : str
        Configuration name, used for logging and output filenames if 'config' missing "module" key.

    Returns
    -------
    module
        The module used to handle projections.
    str
        A name associated with the configuration.
    """
    if not config.get('module'):
        # Specification and run config already together.
        mod = get_interpret_container(config)
        shortmodule = str(config_name)
    elif os.path.splitext(config['module'])[1] in ['.yml', '.yaml']:
        # Specification config in another yaml file.
        import warnings
        warnings.warn(
            "Pointing 'module:' to YAML files is deprecated, please use 'import:'",
            FutureWarning,
        )
        mod = get_interpret_container(config)
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
    config : MutableMapping
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
        return wrap_config(config)

    config = wrap_config(config) # make sure I have a ConfigDict
    
    # Read "import" - relative to fpath, if needed.
    if not import_path.is_absolute():
        if isinstance(fpath, str):
            fpath = Path(fpath)
        import_path = fpath.joinpath(import_path)

    import_config = merge_import_config(
        ConfigDict(get_file_config(import_path), prefix='', master_accessed=config.accessed), # save accessed
        import_path.parent
    )

    return wrap_config(merge(import_config, config))

def standardize(config):
    newconfig = copy.copy(config)

    for key in config:
        asdash = key.replace('_', '-')
        asscore = key.replace('-', '_')
        if '-' in key and asscore not in config:
            newconfig[asscore] = config[key]
        if '_' in key and asdash not in config:
            newconfig[asdash] = config[key]
                
    return wrap_config(newconfig, config)

def merge(parent, child):
    if isinstance(child, MutableMapping):
        return MergedConfigDict(parent, child)

    if not (isinstance(parent, ConfigDict) or isinstance(parent, MergedConfigDict)):
        raise TypeError("parent must be a ConfigDict or MergedConfigDict")

    if child not in parent:
        return parent

    return MergedConfigDict(parent, parent[child])

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
    if isinstance(config, ConfigDict) or isinstance(config, MergedConfigDict):
        return deepcopy(dict(config.items()))

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

def get_interpret_container(config):
    """
    Decide on the main controller, which determines the number of threads.

     - The default number of threads for median and montecarlo mode is
       currently 1, but expected to become 2.
     - The default number of threads for parallelmc and testparallelpe
       is 3.
     - All other mode by default use the single threaded container.
    """
    mode = config['mode']
    if mode in ['median', 'montecarlo']:
        threads = config.get('threads', 1)
    elif mode in ['parallelmc', 'testparallelpe']:
        threads = config.get('threads', 3)
    else:
        threads = config.get('threads', 1)
        
    if threads == 1:
        return importlib.import_module("interpret.container")
    elif threads == 2:
        return importlib.import_module("interpret.twothread_container")
    else:
        return importlib.import_module("interpret.parallel_container")

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

def wrap_config(config, source_config=None):
    """Ensure that a config dictionary is wrapped in a ConfigDict-like object.

    This should be called, rather than ConfigDict, if `config` may be
    a MergedConfigDict or if information is `source_config` needs to
    be maintained.

    Include `source_config` if the content in config is a
    copied-and-edited version of data from `source_config`.

    Parameters
    ----------
    config : MutableMapping
        The configuration dictionary. Could already be a ConfigDict or MergedConfigDict
    source_config : MutableMapping, optional
        Source of content in config. Used to maintain access list.

    """
    
    if isinstance(source_config, ConfigDict):
        newconfig = ConfigDict(config, prefix=source_config.prefix, parent=source_config.parent)
        newconfig.accessed = source_config.accessed # source_config.parent may not be a ConfigDict
        return newconfig

    if isinstance(config, MergedConfigDict):
        return config

    return ConfigDict(config)

class ConfigDict(MutableMapping):
    """Configuration dictionary that monitors key access.

    Acts just like a dict, except that every time a key of this or a
    child dict or list is accessed, that information is logged (in
    self.accessed). This can then be checked for completeness with
    `check_usage`.

    Parameters
    ----------
    config : MutableMapping
        ConfigDict will wrap this config, offering access to its data.
    prefix : str
        For sub-dicts of the top-level config, this specifies the path to this dict.
    master_accessed : set, optional
        For sub-dicts, this is the top-level accessed set to add to.

    """
    def __init__(self, config, prefix='', master_accessed=None):
        if isinstance(config, ConfigDict):
            self.accessed = config.accessed
            self.config = config.config
            if master_accessed is not None:
                assert self.accessed == master_accessed
        else:
            self.config = config
            if master_accessed is not None:
                self.accessed = master_accessed
            else:
                self.accessed = set()
                
        self.prefix = prefix

    def __repr__(self):
        class_name = type(self).__name__
        return f"{class_name}({self.config!r}, prefix={self.prefix!r})"

    def __len__(self):
        return len(self.config)

    def __iter__(self):
        return iter(self.config.keys())

    def __contains__(self, key):
        return key in self.config
        
    def __getitem__(self, key):
        access_key = self.prefix + str(key)
        self.accessed.add(access_key)
        return self.wrapped_get(key)

    def wrapped_get(self, key):
        """Get the given key, returning a wrapped config entry as needed, without recording the access."""
        access_key = self.prefix + str(key)
        value = self.config[key]
        if isinstance(value, dict):
            return ConfigDict(value, prefix=access_key + '.', master_accessed=self.accessed)
        if isinstance(value, list):
            return ConfigList(value, prefix=access_key + '.', master_accessed=self.accessed)
        return value

    def __setitem__(self, key, value):
        """Do not record in accessed until access."""
        self.config[key] = value

    def __delitem__(self, key):
        del self.config[key]

    def items(self):
        return self.config.items()

    def check_usage(self):
        """Look through every key and sub-structures, and return a set of unaccessed entries."""
        missing = set()
        for key in self.config:
            access_key = self.prefix + str(key)
            if access_key not in self.accessed:
                missing.add(access_key)
            value = self.wrapped_get(key)
            if isinstance(value, ConfigDict) or isinstance(value, ConfigList):
                missing.update(value.check_usage())

        return missing

class MergedConfigDict(MutableMapping):
    """Combines configuration dictionaries so both can be accessed.

    This acts like a dictionary containing the keys of
    `copy(parent).update(child)`. It is used to allow sub-dicts of
    configurations to access all ancestor keys. We use this rather
    than an `update` line to support the key-access features in
    ConfigDict.

    Parameters
    ----------
    parent : MutableMapping
        Configuration dictionary that key access falls back to, if missing from child.
    child : MutableMapping
        Main configuration dictionary to return values from.

    """
    def __init__(self, parent, child):
        self.parent = parent
        self.child = child

    def __repr__(self):
        class_name = type(self).__name__
        return f"{class_name}({self.parent!r}, prefix={self.child!r})"

    def __len__(self):
        return len(self.child) + len(self.parent)

    def __iter__(self):
        return iter(list(self.child.keys()) + list(self.parent.keys()))

    def __contains__(self, key):
        return key in self.child or key in self.parent
    
    def __getitem__(self, key):
        if key in self.child:
            return self.child[key]
        else:
            return self.parent[key]

    def __setitem__(self, key, value):
        self.child[key] = value

    def __delitem__(self, key):
        if key in self.child:
            del self.child[key]
        else:
            del self.parent[key]

    def items(self):
        copydict = dict(self.parent.items())
        copydict.update(dict(self.child.items()))
        return copydict.items()
            
class ConfigList(MutableSequence):
    """Wrapper on lists contained in configuration dictionaries to monitor key access.

    Acts just like a list, except that every time a key of this or a
    child dict or list is accessed, that information is logged (in
    self.accessed). This can then be checked for completeness with
    `check_usage`.

    Parameters
    ----------
    configlist : MutableSequence
        ConfigList will wrap this list, offering access to its data.
    prefix : str
        For sub-dicts of the top-level config, this specifies the path to this dict.
    master_accessed : set, optional
        For sub-dicts, this is the top-level accessed set to add to.

    """
    def __init__(self, configlist, prefix, master_accessed=None):
        if isinstance(configlist, ConfigList):
            self.accessed = configlist.accessed
            self.configlist = configlist.configlist
            if master_accessed is not None:
                assert self.accessed == master_accessed
        else:
            self.configlist = configlist
            if master_accessed is not None:
                self.accessed = master_accessed
            else:
                self.accessed = set()

        self.prefix = prefix

    def __len__(self):
        return len(self.configlist)

    def __getitem__(self, index):
        access_key = self.prefix + str(index)
        self.accessed.add(access_key)
        return self.wrapped_get(index)

    def wrapped_get(self, index):
        """Get the given index, returning a wrapped config entry as needed, without recording the access."""
        access_key = self.prefix + str(index)
        value = self.configlist[index]
        if isinstance(value, dict):
            return ConfigDict(value, prefix=access_key + '.', master_accessed=self.accessed)
        if isinstance(value, list):
            return ConfigList(value, prefix=access_key + '.', master_accessed=self.accessed)
        return value

    def __setitem__(self, index, value):
        """Do not record in accessed until access."""
        self.configlist[index] = value

    def __delitem__(self, index):
        del self.configlist[index]

    def insert(self, index, value):
        self.configlist.insert(index, value)
        
    def check_usage(self):
        """Look through every index and sub-structures, and return a list of unaccessed entries."""
        missing = set()
        for ii in range(len(self.configlist)):
            access_key = self.prefix + str(ii)
            if access_key not in self.accessed:
                missing.add(access_key)
            value = self.wrapped_get(ii)
            if isinstance(value, ConfigDict) or isinstance(value, ConfigList):
                missing.update(value.check_usage())

        return missing
