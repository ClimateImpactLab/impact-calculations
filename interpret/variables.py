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
    """Parse variable name for transformations to apply to variables

    Parameters
    ----------
    name : str
        Name to interpret. Assumes the name has no units designated with
        brackets or parenthesis.
    config : dict
        Configuration dictionary.

    Returns
    -------
    openest.generate.selfdocumented.DocumentedFunction
    """
    if ' ** ' in name:
        chunks = name.split(' ** ', 1)
        internal_left = interpret_ds_transform(chunks[0], config)
        internal_right = interpret_ds_transform(chunks[1], config)

        return selfdocumented.DocumentedFunction(lambda ds: internal_left(ds) * internal_right(ds),
                                                 name, lambda x, y: x * y,
                                                 [internal_left, internal_right])

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

    # If can cast into float, simply use as scalar value.
    try:
        use_scalar = float(name)

        # Create a FastDataset populated with the name and scalar...
        def out(ds):
            # Get first available non-coordinate variable.
            noncoord_var = [x for x in ds.variables.keys() if x not in ds.coords.keys()][0]
            new_shape = ds[noncoord_var]._values.shape
            new_coords = list(ds.original_coords)
            darray = fast_dataset.FastDataArray(np.ones(new_shape) * use_scalar,
                                                new_coords, ds)
            return darray

        return selfdocumented.DocumentedFunction(out, name)

    except ValueError:
        pass

    return get_post_process(name, config)


def interpret_wrap_transform(transform, internal):
    if transform[:4] == 'bin(':
        value = float(transform[4:-1]) if '.' in transform else int(transform[4:-1])
        def getbin(ds):
            assert sum(ds.refTemp == value) == 1, "Cannot find the requested temperature cut-off."
            return internal(ds).sel(refTemp=value)
        return selfdocumented.DocumentedFunction(getbin, "Extract bin from weather",
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

    if 'final-t' in config: # also handles 'final-t' + 'within-season' case recursively
        subconfig = copy.copy(config)
        del subconfig['final-t']
        before = post_process(ds, name, subconfig)
        if config['final-t'] < before._values.shape[dataarr.original_coords.index('time')]:
            return before.isel(time=config['final-t'])
            # return fast_dataset.FastDataArray(np.array([before._values[config['final-t']]]), dataarr.original_coords, ds)
        else:
            new_coords = list(dataarr.original_coords)
            new_shape = list(before._values.shape)
            del new_shape[new_coords.index('time')]
            del new_coords[new_coords.index('time')]
            return fast_dataset.FastDataArray(np.zeros(tuple(new_shape)), new_coords, ds)

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

