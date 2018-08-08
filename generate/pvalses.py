"""
Elsewhere in the code, pvals or qvals is an instance of either the
ConstantPvals or OnDemandRandomPvals class from generate/pvalses.py
(which I should have derive from a common superclass).  It's used to
determine the set of p-values for a run, which is used for (1)
determining parameters from the CSVV through collapse_bang, (2)
determining the order of years for historical MC runs, (3) resolving
the uncertainty forecasts for conflict and anything else that is
stochastic.
"""

import os, yaml, time
import numpy as np

def interpret(config):
    if 'pvals' not in config or config['pvals'] == 'median':
        return ConstantPvals(.5)

    if config['pvals'] == 'montecarlo':
        return OnDemandRandomPvals()

    try:
        pval = float(config['pvals'])
    except:
        pval = None

    if pval is not None:
        assert pval > 0 and pval < 1
        return ConstantPvals(pval)

    if isinstance(config['vals'], str):
        return read_pval_file(config['pvals'])

    if isinstance(config['pvals'], dict):
        return load_pvals(config['pvals'])

class ConstantPvals:
    def __init__(self, value):
        self.value = value

    def lock(self):
        pass

    def __getitem__(self, name):
        return ConstantDictionary(self.value)

    def __iter__(self):
        yield ('all', self.value)

class PvalsDictionary(object):
    pass
        
class ConstantDictionary(PvalsDictionary):
    def __init__(self, value):
        self.value = value

    def lock(self):
        pass

    def __getitem__(self, name):
        return self.value

    def get_seed(self, plus=0):
        return None # for MC, have this also increment state

class OnDemandRandomPvals:
    def __init__(self):
        self.dicts = {}
        self.locked = False

    def lock(self):
        self.locked = True
        for key in self.dicts:
            self.dicts[key].lock()

    def __getitem__(self, name):
        mydict = self.dicts.get(name, None)
        if mydict is None and not self.locked:
            mydict = OnDemandRandomDictionary()
            self.dicts[name] = mydict

        return mydict

    def __iter__(self):
        for key in self.dicts:
            yield (key, self.dicts[key].values)

class OnDemandRandomDictionary(PvalsDictionary):
    def __init__(self):
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

    def get_seed(self, plus=0):
        if self.locked:
            if 'seed' not in self.values:
                print "WARNING: Missing seed in locked MC.  Assuming median."
                return None
            return self.values['seed'][0] + plus

        seed = int(time.time()) + plus
        if 'seed' in self.values:
            self.values['seed'].append(seed)
        else:
            self.values['seed'] = [seed]

        return seed

class SingleSDPvals:
    def __init__(self, gamma, quantile):
        self.gamma = gamma
        self.quantile = quantile

    def lock(self):
        pass

    def __getitem__(self, name):
        return SingleSDDictionary(self.gamma, self.quantile)

    def __iter__(self):
        yield ('gamma', self.gamma)
        yield ('quantile', self.quantile)

class SingleSDDictionary(PvalsDictionary):
    def __init__(self, gamma, quantile):
        self.gamma = gamma
        self.quantile = quantile

    def lock(self):
        pass
            
    def __getitem__(self, name):
        if name == self.gamma:
            return self.quantile
        else:
            return 0.5

    def get_seed(self, plus=0):
        return self # collapse_bang can handle this
    
def get_pval_file(targetdir):
    return os.path.join(targetdir, "pvals.yml")

def make_pval_file(targetdir, pvals):
    with open(get_pval_file(targetdir), 'w') as fp:
        fp.write(yaml.dump(dict(pvals)))
    try:
        os.chmod(get_pval_file(targetdir), 0664)
    except:
        pass # This can fail if someone else created the file

def has_pval_file(targetdir):
    return os.path.exists(get_pval_file(targetdir))

def read_pval_file(path, lock=False):
    if not os.path.isfile(path):
        path = get_pval_file(path) # assume it's a directory containing pvals.yml
        
    with open(path, 'r') as fp:
        pvals = yaml.load(fp)

        return load_pvals(pvals, lock=lock)

def load_pvals(pvals, lock=False):
    if len(pvals) == 1 and 'all' in pvals:
        return ConstantPvals(pvals['all'])

    odrp = OnDemandRandomPvals()
    for name in pvals:
        odrp.dicts[name] = OnDemandRandomDictionary()
        odrp.dicts[name].values = pvals[name]

    if lock:
        odrp.lock()

    return odrp
