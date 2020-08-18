import yaml, copy

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
            
