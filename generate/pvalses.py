import os, yaml, time
import numpy as np

class ConstantPvals:
    def __init__(self, value):
        self.value = value

    def lock(self):
        pass

    def __getitem__(self, name):
        return ConstantDictionary(self.value)

    def __iter__(self):
        yield ('all', self.value)

class ConstantDictionary:
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

class OnDemandRandomDictionary:
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
            return self.values['seed'][0] + plus

        seed = int(time.time()) + plus
        if 'seed' in self.values:
            self.values['seed'].append(seed)
        else:
            self.values['seed'] = [seed]

        return seed

def get_pval_file(targetdir):
    return os.path.join(targetdir, "pvals.yml")

def make_pval_file(targetdir, pvals):
    with open(get_pval_file(targetdir), 'w') as fp:
        fp.write(yaml.dump(dict(pvals)))

def has_pval_file(targetdir):
    return os.path.exists(get_pval_file(targetdir))

def read_pval_file(targetdir, lock=False):
    with open(get_pval_file(targetdir), 'r') as fp:
        pvals = yaml.load(fp)

        if len(pvals) == 1 and 'all' in pvals:
            return ConstantPvals(pvals['all'])

        odrp = OnDemandRandomPvals()
        for name in pvals:
            odrp.dicts[name] = OnDemandRandomDictionary()
            odrp.dicts[name].values = pvals[name]
            odrp.dicts[name].locked = lock

        odrp.dicts = pvals
        odrp.locked = lock

        return odrp
