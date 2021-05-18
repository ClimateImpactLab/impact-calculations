"""
Elsewhere in the code, pvals or qvals is an instance of either the
ConstantPvals or OnDemandRandomPvals class from generate/pvalses.py.
It's used to determine the set of p-values for a run, which is used
for (1) determining parameters from the CSVV through collapse_bang,
(2) determining the order of years for historical MC runs, (3)
resolving the uncertainty forecasts for conflict and anything else
that is stochastic.
"""

import os, yaml, zlib
import numpy as np

## These dictionaries (keys in the top-level Pvals object) have common values across sectors
cross_sector_dictionaries = ['histclim']

def interpret(config, relative_location):
    """Construct an appropriate `Pvals` object for the given configured
    run.

    Parameters
    ----------
    config : dict
        A run configuration dictionary.
    relative_location : list of str
        list of features of the targetdir common across sectors.

    Returns
    -------
    `Pvals`
    """
    if 'pvals' not in config or config['pvals'] == 'median':
        return ConstantPvals(.5)

    if config['pvals'] == 'montecarlo':
        return OnDemandRandomPvals(relative_location)

    try:
        pval = float(config['pvals'])
    except Exception as ex:
        print("Exception, but assigning None:")
        print(ex)
        pval = None

    if pval is not None:
        assert pval > 0 and pval < 1
        return ConstantPvals(pval)

    if isinstance(config['pvals'], str):
        return read_pval_file(config['pvals'], relative_location)

    if isinstance(config['pvals'], dict):
        return load_pvals(config['pvals'], relative_location)

def get_montecarlo_pvals(config, relative_location):
    # Use "pvals" seeds from config, if available.
    if 'pvals' in list(config.keys()):
        return load_pvals(config['pvals'], relative_location)
    else:
        return OnDemandRandomPvals(relative_location)

## Abstract base classes
    
class Pvals:
    # Future work: Implement this as a Mapping
    def lock(self):
        raise NotImplementedError()

    def __getitem__(self, name):
        raise NotImplementedError()

    def __iter__(self):
        raise NotImplementedError()

class PvalsDictionary:
    # Future work: Implement this as a MutableMapping
    def lock(self):
        raise NotImplementedError()

    def __getitem__(self, name):
        raise NotImplementedError()

    def get_seed(self, name, plus=0):
        raise NotImplementedError()

# ConstantPvals classes

class ConstantPvals(Pvals):
    """ConstantPvals always return the same value."""
    def __init__(self, value):
        self.value = value

    def lock(self):
        pass

    def __getitem__(self, name):
        return ConstantDictionary(self.value)

    def __iter__(self):
        yield ('all', self.value)

class ConstantDictionary(PvalsDictionary):
    def __init__(self, value):
        self.value = value

    def lock(self):
        pass

    def __getitem__(self, name):
        return self.value

    def get_seed(self, name, plus=0):
        return None # for MC, have this also increment state

# OnDemandRandomPvals classes

class OnDemandRandomPvals(Pvals):
    """OnDemandRandomPvals constructs random numbers as needed."""
    def __init__(self, relative_location):
        self.relative_location = relative_location
        self.dicts = {}
        self.locked = False

    def lock(self):
        self.locked = True
        for key in self.dicts:
            self.dicts[key].lock()

    def __getitem__(self, name):
        mydict = self.dicts.get(name, None)
        if mydict is None and not self.locked:
            mydict = OnDemandRandomDictionary(self.relative_location if name in cross_sector_dictionaries else None)
            self.dicts[name] = mydict

        return mydict

    def __iter__(self):
        for key in self.dicts:
            yield (key, self.dicts[key].values)

class OnDemandRandomDictionary(PvalsDictionary):
    def __init__(self, relative_location):
        self.relative_location = relative_location
        self.values = {}
        self.locked = False

    def lock(self):
        self.locked = True

    def __getitem__(self, name):
        value = self.values.get(name, np.nan)
        if np.isnan(value) and not self.locked:
            value = np.random.uniform()
            self.values[name] = value

        return value

    def get_seed(self, name, plus=0):
        fullname = "seed-%s" % name
        if self.locked:
            if fullname not in self.values:
                print("WARNING: Missing seed in locked MC.  Assuming median.")
                return None
            return self.values[fullname] + plus

        if fullname in self.values:
            return self.values[fullname]

        if self.relative_location is None:
            # Not a cross-sector dictionary
            seed = np.random.SeedSequence().entropy + plus
        else:
            seed = cross_sector_seed(self.relative_location, name, plus)
        self.values[fullname] = seed
        return seed

    def set_seed(self, name, seed):
        assert not self.locked
        fullname = "seed-%s" % name
        self.values[fullname] = seed

## Placeholder Pvals, not able to be used (used by parallel)

class PlaceholderPvals(Pvals):
    def __init__(self, config, relative_location):
        self.config = config
        self.relative_location = relative_location

    def get_montecarlo_pvals(self):
        return get_montecarlo_pvals(self.config, self.relative_location)
        
    def lock(self):
        raise AttributeError("PlaceholderPvals does not support standard methods")

    def __getitem__(self, name):
        raise AttributeError("PlaceholderPvals does not support standard methods")

    def __iter__(self):
        raise AttributeError("PlaceholderPvals does not support standard methods")
        
## Helper functions

def get_pval_file(targetdir):
    return os.path.join(targetdir, "pvals.yml")

def make_pval_file(targetdir, pvals):
    with open(get_pval_file(targetdir), 'w') as fp:
        fp.write(yaml.dump(dict(pvals)))
    try:
        os.chmod(get_pval_file(targetdir), 0o664)
    except Exception as ex:
        print("Exception but passing:")
        print(ex)

def has_pval_file(targetdir):
    return os.path.exists(get_pval_file(targetdir))

def read_pval_file(path, relative_location, lock=False):
    if not os.path.isfile(path):
        path = get_pval_file(path) # assume it's a directory containing pvals.yml
        
    with open(path, 'r') as fp:
        pvals = yaml.load(fp)

        if pvals is None:
            return None
        
        return load_pvals(pvals, relative_location, lock=lock)

def load_pvals(pvals, relative_location, lock=False):
    if len(pvals) == 1 and 'all' in pvals:
        return ConstantPvals(pvals['all'])

    odrp = OnDemandRandomPvals(relative_location)
    for name in pvals:
        odrp.dicts[name] = OnDemandRandomDictionary(relative_location if name in cross_sector_dictionaries else None)
        odrp.dicts[name].values = pvals[name]

    if lock:
        odrp.lock()

    return odrp

def cross_sector_seed(relative_location, key="", value=0):
    hashkey = "".join(relative_location) + key
    return zlib.crc32(str.encode(hashkey), value)
