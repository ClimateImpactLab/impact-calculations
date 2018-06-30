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
