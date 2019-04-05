import re, copy
import numpy as np
from openest.generate import fast_dataset, selfdocumented
from datastore import irvalues

re_dotsplit = re.compile("\.(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)")

def needs_interpret(name, config):
    if ' - ' in name or ' * ' in name or '.' in name:
        return True
    if 'final-t' in config or 'within-season' in config:
        return True
    return False

def interpret_ds_transform(name, config):
    if ' - ' in name:
        chunks = name.split(' - ', 1)
        internal_left = interpret_ds_transform(chunks[0], config)
        internal_right = interpret_ds_transform(chunks[1], config)

        return selfdocumented.DocumentedFunction(lambda ds: internal_left(ds) - internal_right(ds),
                                                 name, lambda x, y: x - y,
                                                 [internal_left, internal_right])

    if ' * ' in name:
        chunks = name.split(' * ', 1)
        internal_left = interpret_ds_transform(chunks[0], config)
        internal_right = interpret_ds_transform(chunks[1], config)

        return selfdocumented.DocumentedFunction(lambda ds: internal_left(ds) * internal_right(ds),
                                                 name, lambda x, y: x * y,
                                                 [internal_left, internal_right])

    if '.' in name:
        chunks = re_dotsplit.split(name)
        if len(chunks) > 1:
            internal = get_post_process(chunks[0], config)
            for chunk in chunks[1:]:
                internal = interpret_wrap_transform(chunk, internal)
            return internal

    return get_post_process(name, config)

def interpret_wrap_transform(transform, internal):
    if transform[:4] == 'bin(':
        value = float(transform[4:-1]) if '.' in transform else int(transform[4:-1])
        return selfdocumented.DocumentedFunction(lambda ds: internal(ds).sel(refTemp=value),
                                                 "Extract bin from weather",
                                                 docargs=[internal, value])
    
    assert False, "Unknown transform" + transform

def get_post_process(name, config):
    if 'final-t' in config:
        return selfdocumented.DocumentedFunction(lambda ds: post_process(ds, name, config), "Select time %d" % config['final-t'], docargs=[name])
    
    if 'within-season' in config:
        return selfdocumented.DocumentedFunction(lambda ds: post_process(ds, name, config), "Limit to within season", docargs=[name])

    return selfdocumented.DocumentedFunction(lambda ds: ds[name], "Extract from weather", docfunc=lambda x: x, docargs=[name])
    
def post_process(ds, name, config):
    dataarr = ds[name]

    if 'final-t' in config:
        subconfig = copy.copy(config)
        del subconfig['final-t']
        before = post_process(ds, name, subconfig)
        if config['final-t'] < len(before._values):
            return fast_dataset.FastDataArray(np.array([before._values[config['final-t']]]), dataarr.original_coords, ds)
        else:
            return fast_dataset.FastDataArray(np.array([0.]), dataarr.original_coords, ds)
    
    if 'within-season' in config:
        if len(dataarr) == 24:
            culture = irvalues.get_file_cached(config['within-season'], irvalues.load_culture_months).get(ds.region, None)
            if culture is not None:
                return fast_dataset.FastDataArray(dataarr[(culture[0]-1):culture[1]], dataarr.original_coords, ds)
        elif len(dataarr) == 730:
            culture = irvalues.get_file_cached(config['within-season'], irvalues.load_culture_doys).get(ds.region, None)
            if culture is not None:
                return fast_dataset.FastDataArray(dataarr[(culture[0]-1):culture[1]], dataarr.original_coords, ds)
        else:
            print ds
            assert False, "Not expected number of elements: %s" % str(dataarr.shape)

    return dataarr

def read_range(text):
    items = map(lambda x: x.strip(), text.split(','))
    indices = []
    for item in items:
        if ':' in item:
            limits = item.split(':')
            indices.extend(range(int(limits[0]) - 1, int(limits[1])))
        else:
            indices.append(int(item) - 1)

    return np.array(indices)

