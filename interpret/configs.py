import copy

def merge(parent, child):
    result = copy.copy(parent)
    result.update(child)
    return result
