import os, shutil
import numpy as np
import helpers.header as headre

def string_to_bounds(name):
    parts = name.split('_')
    if len(parts) == 2:
        if 'to' in parts[1]:
            parts = [parts[0]] + parts[1].split('to')
        else:
            assert parts[1][:5].lower() == 'under' or parts[1][:4].lower() == 'over', "If only two parts in bin name, must be 'under...' or 'over...' for " + name
            if parts[1][:5].lower() == 'under':
                parts = [parts[0], 'ninf', parts[1][5:]]
            else:
                parts = [parts[0], parts[1][4:], 'inf']

    if parts[1][-1] == 'F':
        parts[1] = str((float(parts[1][:-1]) - 32) / 1.8) + 'C'
    if parts[2][-1] == 'F':
        parts[2] = str((float(parts[2][:-1]) - 32) / 1.8) + 'C'

    assert parts[1][-1] == 'C' or parts[1].lower() == 'ninf', name + " lower bound not a recognized temperature."
    assert parts[2][-1] == 'C' or parts[2].lower() == 'inf', name + " upper bound not a recognized temperature."

    if parts[1].lower() == 'ninf':
        lower = -np.inf
    else:
        if parts[1][0] == 'n':
            parts[1] = '-'+ parts[1][1:]
        lower =float(parts[1][:-1])

    if parts[2].lower() == 'inf':
        upper = np.inf
    else:
        if parts[2][0] == 'n':
            parts[2] = '-' + parts[2][1:]
        upper = float(parts[2][:-1])

    return parts[0], lower, upper

def bounds_to_string(name, lower, upper):
    if lower == -np.inf:
        lower = '-Inf'
    else:
        lower = int(lower)
    if upper == np.inf:
        upper = 'Inf'
    else:
        upper = int(upper)

    return '_'.join([name, str(lower).replace('-', 'n') + 'C', str(upper).replace('-', 'n') + 'C'])

def clear_dir(outdir):
    if os.path.exists(outdir):
        shutil.rmtree(outdir)
    os.mkdir(outdir)

def all_predictors(outdir, dependencies):
    for filename in os.listdir(outdir):
        bin, binlo, binhi = string_to_bounds(filename[:-4])

        with open(os.path.join(outdir, filename), 'r') as fp:
            headre.deparse(fp, dependencies)
            yield binlo, binhi, fp

def get_predcol(row, headrow, predcol, binlo=None, binhi=None):
    """Get a predictor column from a table, handling special cases.
    binlo and binhi are only used currently for meandays_self."""

    if predcol[:4] == 'log ':
        return np.log(get_predcol(row, headrow, predcol[4:]))

    if predcol == 'meandays_self':
        return get_predcol(row, headrow, bounds_to_string('meandays', binlo, binhi))

    return float(row[headrow.index(predcol)])

