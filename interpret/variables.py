import re, copy
from contextlib import suppress
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


def wrap_as_selfdoc(as_selfdoc, func, description=None, docfunc=None, docargs=None):
    if as_selfdoc:
        return selfdocumented.DocumentedFunction(func, description, docfunc, docargs)
    else:
        return func
    

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
    function-like:
      openest.generate.selfdocumented.DocumentedFunction or function
    """
    as_selfdoc = config.get('mode', 'NA') == 'writecalcs'
    
    # If can cast name into float (no ValueError), simply use as float value.
    with suppress(ValueError):
        use_scalar = float(name)
        # Create a FastDataset populated with the name and scalar...
        def out(ds):
            # Get first available non-coordinate variable.
            noncoord_var = [x for x in list(ds.variables.keys()) if x not in list(ds.coords.keys())][0]
            new_shape = ds[noncoord_var]._values.shape
            new_coords = list(ds.original_coords)
            darray = fast_dataset.FastDataArray(np.ones(new_shape) * use_scalar,
                                                new_coords, ds)
            return darray

        return wrap_as_selfdoc(as_selfdoc, out, name)

    # Otherwise interpret variable names and possible implied transformations.
    if ' ** ' in name:
        chunks = name.split(' ** ', 1)
        internal_left = interpret_ds_transform(chunks[0], config)
        internal_right = interpret_ds_transform(chunks[1], config)

        return wrap_as_selfdoc(as_selfdoc, lambda ds: internal_left(ds) * internal_right(ds),
                               name, lambda x, y: x * y,
                               [internal_left, internal_right])

    if ' - ' in name:
        chunks = name.split(' - ', 1)
        internal_left = interpret_ds_transform(chunks[0], config)
        internal_right = interpret_ds_transform(chunks[1], config)

        return wrap_as_selfdoc(as_selfdoc, lambda ds: internal_left(ds) - internal_right(ds),
                               name, lambda x, y: x - y,
                               [internal_left, internal_right])

    if ' * ' in name:
        chunks = name.split(' * ', 1)
        internal_left = interpret_ds_transform(chunks[0], config)
        internal_right = interpret_ds_transform(chunks[1], config)

        return wrap_as_selfdoc(as_selfdoc, lambda ds: internal_left(ds) * internal_right(ds),
                               name, lambda x, y: x * y,
                               [internal_left, internal_right])

    if '.' in name:
        chunks = re_dotsplit.split(name)
        if len(chunks) > 1:
            internal = get_post_process(chunks[0], config, as_selfdoc)
            for chunk in chunks[1:]:
                internal = interpret_wrap_transform(chunk, internal, as_selfdoc)
            return internal

    return get_post_process(name, config, as_selfdoc)


def interpret_wrap_transform(transform, internal, as_selfdoc):
    if transform[:4] == 'bin(':
        value = float(transform[4:-1]) if '.' in transform else int(transform[4:-1])
        validated_sel_setup = None
        def getbin(ds):
            nonlocal validated_sel_setup
            internalvar = internal(ds)
            if validated_sel_setup is None: # only do this once
                assert sum(ds.refTemp == value) == 1, "Cannot find the requested temperature cut-off."
                validated_sel_setup = internalvar.sel_setup(refTemp=value)
            return internalvar.sel_apply(validated_sel_setup)
        return wrap_as_selfdoc(as_selfdoc, getbin, "Extract bin from weather",
                               docargs=[internal, value])

    assert False, "Unknown transform" + transform

    
def get_post_process(name, config, as_selfdoc):
    if 'final-t' in config:
        return wrap_as_selfdoc(as_selfdoc, lambda ds: post_process_final_t(ds, ds[name], name, config), "Select time %d" % config['final-t'], docargs=[name])

    if 'within-season' in config:
        return wrap_as_selfdoc(as_selfdoc, lambda ds: post_process_within_season(ds, ds[name], name, config), "Limit to within season", docargs=[name])

    return wrap_as_selfdoc(as_selfdoc, lambda ds: ds[name], "Extract from weather", docfunc=lambda x: x, docargs=[name])

def post_process(ds, dataarr, name, config):
    if 'final-t' in config: # also handles 'final-t' + 'within-season' case recursively
        return post_process_final_t(ds, dataarr, name, config)

    if 'within-season' in config:
        return post_process_within_season(ds, dataarr, name, config)

    return dataarr


def post_process_final_t(ds, dataarr, name, config):
    subconfig = copy.copy(config)
    del subconfig['final-t']
    before = post_process(ds, dataarr, name, subconfig)
    if config['final-t'] < before._values.shape[dataarr.original_coords.index('time')]:
        return before.isel(time=config['final-t'])
        # return fast_dataset.FastDataArray(np.array([before._values[config['final-t']]]), dataarr.original_coords, ds)
    else:
        new_coords = list(dataarr.original_coords)
        new_shape = list(before._values.shape)
        del new_shape[new_coords.index('time')]
        del new_coords[new_coords.index('time')]
        return fast_dataset.FastDataArray(np.zeros(tuple(new_shape)), new_coords, ds)


def post_process_within_season(ds, dataarr, name, config):
    if len(dataarr) == 24:
        culture = irvalues.get_file_cached(config['within-season'], irvalues.load_culture_months).get(ds.region, None)
        if culture is not None:
            return fast_dataset.FastDataArray(dataarr[(culture[0]-1):culture[1]], dataarr.original_coords, ds)
    elif len(dataarr) == 730:
        culture = irvalues.get_file_cached(config['within-season'], irvalues.load_culture_doys).get(ds.region, None)
        if culture is not None:
            return fast_dataset.FastDataArray(dataarr[(culture[0]-1):culture[1]], dataarr.original_coords, ds)
    else:
        print(ds)
        assert False, "Not expected number of elements: %s" % str(dataarr.shape)

    return dataarr

##### Univariate versions

def interpret_univariate_transform(name, config):
    """Parse variable name to generate a univariate transformation

    Parameters
    ----------
    name : str
        Name to interpret. Assumes the name has no units designated with
        brackets or parenthesis.
    config : dict
        Configuration dictionary.

    Returns
    -------
    (function, variable or None) or (None, None)
        Returns (None, None) if a univariate interpretation is ambiguous; variable may be None or str
    """

    # If can cast name into float (no ValueError), simply use as float value.
    with suppress(ValueError):
        use_scalar = float(name)
        return lambda xxs: np.ones(xxs.shape) * use_scalar, None

    # Otherwise interpret variable names and possible implied transformations.
    if ' ** ' in name:
        chunks = name.split(' ** ', 1)
        internal_left, variable_left = interpret_univariate_transform(chunks[0], config)
        internal_right, variable_right = interpret_univariate_transform(chunks[1], config)

        return validate_binary_univariate(internal_left, variable_left, internal_right, variable_right,
                                          lambda xxs, yys: xxs * yys)

    if ' - ' in name:
        chunks = name.split(' - ', 1)
        internal_left, variable_left = interpret_univariate_transform(chunks[0], config)
        internal_right, variable_right = interpret_univariate_transform(chunks[1], config)

        return validate_binary_univariate(internal_left, variable_left, internal_right, variable_right,
                                          lambda xxs, yys: xxs - yys)

    if ' * ' in name:
        chunks = name.split(' * ', 1)
        internal_left, variable_left = interpret_univariate_transform(chunks[0], config)
        internal_right, variable_right = interpret_univariate_transform(chunks[1], config)

        return validate_binary_univariate(internal_left, variable_left, internal_right, variable_right,
                                          lambda xxs, yys: xxs * yys)

    if '.' in name:
        chunks = re_dotsplit.split(name)
        if len(chunks) > 1:
            variable = chunks[0]
            internal = lambda xxs: xxs
            for chunk in chunks[1:]:
                internal, variable = interpret_wrap_univariate_transform(chunk, internal, variable)
            return internal, variable

    return lambda xxs: xxs, name


def validate_binary_univariate(internal_left, variable_left, internal_right, variable_right, combine):
        if internal_left is None or internal_right is None:
            return None, None
        if variable_left is not None and variable_right is not None and variable_left != variable_right:
            return None, None

        variable = variable_left if variable_left is not None else variable_right

        return lambda xxs: combine(internal_left(xxs), internal_right(xxs)), variable


def interpret_wrap_univariate_transform(transform, internal, variable):
    if transform[:4] == 'bin(':
        return internal, variable + transform

    assert False, "Unknown transform" + transform


##### Helper functions

def read_range(text):
    items = [x.strip() for x in text.split(',')]
    indices = []
    for item in items:
        if ':' in item:
            limits = item.split(':')
            indices.extend(list(range(int(limits[0]) - 1, int(limits[1]))))
        else:
            indices.append(int(item) - 1)

    return np.array(indices)

