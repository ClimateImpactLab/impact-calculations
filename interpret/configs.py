import yaml, copy

def standardize(config):
    for key in config:
        asdash = key.replace('_', '-')
        asscore = key.replace('-', '_')
        if '-' in key and asscore not in config:
            config[asscore] = config[key]
        if '_' in key and asdash not in config:
            config[asdash] = config[key]
                
    return config

def merge(parent, child):
    result = copy.copy(parent)
    result.update(child)
    return result
