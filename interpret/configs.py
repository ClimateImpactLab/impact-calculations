import yaml, copy
from pathlib import Path
from impactlab_tools.utils.files import get_file_config


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
            
