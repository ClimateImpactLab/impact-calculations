import csv, copy, re
import numpy as np
from scipy.stats import norm
import metacsv
from generate import pvalses
from scipy.stats import multivariate_normal
import csvvfile_legacy

def read(filename):
    with open(filename, 'rU') as fp:
        attrs, coords, variables = metacsv.read_header(fp, parse_vars=True)

        # Clean up variables
        for variable in variables:
            fullunit = variable[1]['unit']
            if ']' in fullunit:
                variable[1]['unit'] = fullunit[:fullunit.index(']')]

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
        row[0] = row[0].strip()

        if row[0] in ['observations', 'prednames', 'covarnames', 'gamma', 'gammavcv', 'residvcv']:
            data[row[0]] = []
            variable_reading = row[0]
        else:
            if variable_reading is None:
                print "No variable queued."
                print row
            assert variable_reading is not None
            if len(row) == 1:
                row = row[0].split(',')
            if len(row) == 1:
                row = row[0].split('\t')
            if len(row) == 1:
                row = re.split(r'\s', row[0])
            data[variable_reading].append(map(lambda x: x.strip(), row))

    data['observations'] = float(data['observations'][0][0])
    data['prednames'] = data['prednames'][0]
    data['covarnames'] = data['covarnames'][0]
    data['gamma'] = np.array(map(float, data['gamma'][0]))
    data['gammavcv'] = np.array(map(lambda row: map(float, row), data['gammavcv']))
    data['residvcv'] = np.array(map(lambda row: map(float, row), data['residvcv']))

    return data

def collapse_bang(data, seed):
    """collapse_bang draws from the multivariate uncertainty in the parameters of a CSVV, and changes those values accordingly."""
    if seed == None:
        data['gammavcv'] = None
    elif isinstance(seed, pvalses.PvalsDictionary):
        for ii in range(len(data['gamma'])):
            print ii, norm.ppf(seed[ii]) * np.sqrt(data['gammavcv'][ii, ii])
            data['gamma'][ii] = data['gamma'][ii] + norm.ppf(seed[ii]) * np.sqrt(data['gammavcv'][ii, ii])
        data['gammavcv'] = None # this will cause errors if used again
    else:
        np.random.seed(seed)
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

def subset(csvv, toinclude):
    """Create a CSVV object with the contents of a subset of the variables in csvv.
    `toinclude` may be either a list of predictor names from prednames, or a list of indices."""
    if isinstance(toinclude[0], str):
        toinclude = map(lambda predname: predname in toinclude, csvv['prednames'])
        toinclude = np.where(toinclude)[0]
    else:
        toinclude = np.array(toinclude)

    subcsvv = copy.copy(csvv)
    subcsvv['prednames'] = [csvv['prednames'][ii] for ii in toinclude]
    subcsvv['covarnames'] = [csvv['covarnames'][ii] for ii in toinclude]
    subcsvv['gamma'] = csvv['gamma'][toinclude]
    if 'gammavcv' in csvv and csvv['gammavcv'] is not None:
        subcsvv['gammavcv'] = csvv['gammavcv'][toinclude, toinclude]

    return subcsvv

def filtered(csvv, func):
    toinclude = filter(lambda ii: func(csvv['prednames'][ii], csvv['covarnames'][ii]), range(len(csvv['prednames'])))
    return subset(csvv, toinclude)

def get_gamma(csvv, predname, covarname):
    for ii in range(len(csvv['gamma'])):
        if csvv['prednames'][ii] == predname and csvv['covarnames'][ii] == covarname:
            return csvv['gamma'][ii]

    return None
