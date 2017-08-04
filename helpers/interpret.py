import numpy as np

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

