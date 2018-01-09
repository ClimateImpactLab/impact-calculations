import re
import numpy as np
import irvalues

re_dotsplit = re.compile("\.(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)")

def interpret_ds_transform(name, config):
    if ' - ' in name:
        chunks = name.split(' - ', 1)
        internal_left = interpret_ds_transform(chunks[0], config)
        internal_right = interpret_ds_transform(chunks[1], config)

        return lambda ds: internal_left(ds) - internal_right(ds)
    
    if '.' in name:
        chunks = re_dotsplit.split(name)
        if len(chunks) > 1:
            internal = lambda ds: post_process(ds[chunks[0]], ds.region, config)
            for chunk in chunks[1:]:
                internal = interpret_wrap_transform(chunk, internal)
            return internal

    return lambda ds: post_process(ds[name], ds.region, config)

def interpret_wrap_transform(transform, internal):
    if transform[:4] == 'bin(':
        value = float(transform[4:-1])
        return lambda ds: internal(ds).sel(bin_edges=value)

    assert False, "Unknown transform" + transform

def post_process(data, region, config):
    if 'within-season' in config:
        culture = irvalues.get_file_cached(config['within-season'])[region]
        assert len(data) == 12
        return sum(data[(culture[0]-1):(culture[1]-1)])

    return data

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

