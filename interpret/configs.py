import yaml

def standardize(config):
    for key in config:
        asdash = key.replace('_', '-')
        asscore = key.replace('-', '_')
        if '-' in key and asscore not in config:
            config[asscore] = config[key]
        if '_' in key and asdash not in config:
            config[asdash] = config[key]

    return config
