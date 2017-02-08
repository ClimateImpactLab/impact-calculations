import csv
import numpy as np
import metacsv
from scipy.stats import multivariate_normal
import csvvfile_legacy

def read(filename):
    with open(filename, 'r') as fp:
        attrs, coords, variables = metacsv.read_header(fp, parse_vars=True)
        data = {'attrs': attrs, 'variables': variables, 'coords': coords}

        if 'csvv-version' in attrs:
            if attrs['csvv-version'] == 'girdin-2017-01-10':
                return read_girdin(data, fp)
            else:
                raise ValueError("Unknown version " + attrs['csvv-version'])
        else:
            print "Warning: Using unsupported no-version CSVV reader."
            return csvvfile_legacy.read(data, fp)

def read_girdin(data, fp):
    reader = csv.reader(fp)
    variable_reading = None

    for row in reader:
        if len(row) == 0 or (len(row) == 1 and len(row[0].strip()) == 0):
            continue

        if row[0] in ['observations', 'prednames', 'covarnames', 'gamma', 'gammavcv', 'residvcv']:
            data[row[0]] = []
            variable_reading = row[0]
        else:
            if variable_reading is None:
                print "No variable queued."
                print row
            assert variable_reading is not None
            data[variable_reading].append(map(lambda x: x.strip(), row))

    data['observations'] = float(data['observations'][0][0])
    data['prednames'] = data['prednames'][0]
    data['covarnames'] = data['covarnames'][0]
    data['gamma'] = np.array(map(float, data['gamma'][0]))
    data['gammavcv'] = np.array(map(lambda row: map(float, row), data['gammavcv']))
    data['residvcv'] = np.array(map(lambda row: map(float, row), data['residvcv']))

    return data

def collapse_bang(data, seed):
    if seed == None:
        data['gammavcv'] = None
    else:
        data['gamma'] = multivariate_normal.rvs(data['gamma'], data['gammavcv'])
        data['gammavcv'] = None # this will cause errors if used again

def binnames(xxlimits, prefix):
    names = []
    for ii in range(len(xxlimits)-1):
        names.append(prefix + '_' + binname_part(xxlimits[ii]) + '_' + binname_part(xxlimits[ii+1]))

    return names

def binname_part(xxlimit):
    if xxlimit < 0:
        part = 'n'
        xxlimit = abs(xxlimit)
    else:
        part = ''

    if xxlimit == np.inf:
        part += 'InfC'
    else:
        part += str(xxlimit) + 'C'

    return part
    
