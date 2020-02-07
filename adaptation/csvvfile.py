"""Functions to handle the data in CSVV files.

CSVV files contain the coefficients and variance-covariance terms from
a regression.  They use the MetaCSV format to self-document.  For a
description of CSVV files, see docs/CSVV File Format
Specification.pdf.

"""

import csv, copy, re
import numpy as np
import metacsv
from scipy.stats import multivariate_normal
import csvvfile_legacy

def read(filename):
    """Interpret a CSVV file into a dictionary of the included information.

    Specific implementation is described in the two CSVV version
    readers, `read_girdin` and `csvvfile_legacy.read`.
    """

    with open(filename, 'rU') as fp:
        attrs, coords, variables = metacsv.read_header(fp, parse_vars=True)

        # Clean up variables
        for variable in variables:
            assert isinstance(variable[1], dict), "Variable definition '%s' malformed." % str(variable[1])
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
    """Interpret a Girdin version CSVV file into a dictionary of the
    included inforation.

    A Girdin CSVV has a lists of predictor and covariate names, which
    are matched up one-for-one.  This offered more flexibility and
    clarity than the previous version of CSVV files.

    Parameters
    ----------
    data : dict
        Meta-data from the MetaCSV description.
    fp : file pointer
        File pointer to the start of the file content.

    Returns
    -------
    dict
        Dictionary with MetaCSV information and the predictor and
    covariate information.
    """
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
    else:
        np.random.seed(seed)
        data['gamma'] = multivariate_normal.rvs(data['gamma'], data['gammavcv'])
        data['gammavcv'] = None # this will cause errors if used again

def binnames(xxlimits, prefix):
    """Construct the string that names a given bin, from its limits.

    Bin names as defined in CSVVs and weather files must contain only
    alphanumeric characters and underscores, so this function
    translates a bin definition into these bin names. A typical
    `xxlimits` list might be: [-inf, -1, inf].

    Supposing that the prefix is set to "bin_", this would be
    translated into two bin names: "bin_nInfC_n1C" and "bin_n1C_InfC".

    Parameters
    ----------
    xxlimits : sequence of float
        The sequence of points that defines the limits from one bin to
    another.
    prefix : str
        A prefix prepended to each bin name.

    Returns
    -------
    sequence of str
        The sequence for names for each bin.
    """

    names = []
    for ii in range(len(xxlimits)-1):
        names.append(prefix + '_' + binname_part(xxlimits[ii]) + '_' + binname_part(xxlimits[ii+1]))

    return names

def binname_part(xxlimit):
    """Construct the string for a limit of a temperature bin.

    This is a helper function for `binnames`.

    Parameters
    ----------
    xxlimit : float
        One limit of a temperature

    Returns
    -------
    str
        The string for how this limit is described in a bin name.
    """

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
    `toinclude` may be either a list of predictor names from prednames, or a list of indices or booleans."""
    if not isinstance(toinclude, slice):
        if isinstance(toinclude[0], str):
            toinclude = map(lambda predname: predname in toinclude, csvv['prednames'])
            toinclude = np.nonzero(toinclude)[0]
        elif isinstance(toinclude[0], bool):
            toinclude = np.nonzero(toinclude)[0]
        else:
            toinclude = np.array(toinclude)
        toinclist = toinclude
    else:
        toinclist = range(toinclude.start, toinclude.stop)

    subcsvv = copy.copy(csvv)
    subcsvv['prednames'] = [csvv['prednames'][ii] for ii in toinclist]
    subcsvv['covarnames'] = [csvv['covarnames'][ii] for ii in toinclist]
    subcsvv['gamma'] = csvv['gamma'][toinclude]
    if 'gammavcv' in csvv and csvv['gammavcv'] is not None:
        assert isinstance(toinclude, slice), "The uncertainty must be collapsed first."
        subcsvv['gammavcv'] = csvv['gammavcv'][toinclude, toinclude]

    return subcsvv

def filtered(csvv, func):
    """Return a CSVV object for a subset of the parameters or covariates
    in the file.

    Parameters
    ----------
    csvv : dict
        The dictionary returned from a CSVV `read` operation.
    func : function(predname, covarname) -> bool
        The filtering function, returning true for terms that should remain.

    Returns
    -------
    dict
        A CSVV dictionary for a subset of the original coefficients.
    """
    toinclude = filter(lambda ii: func(csvv['prednames'][ii], csvv['covarnames'][ii]), range(len(csvv['prednames'])))
    return subset(csvv, toinclude)

def get_gamma(csvv, predname, covarname):
    """Return a single coefficient for the interaction between a predictor and a covariate."""
    for ii in range(len(csvv['gamma'])):
        if csvv['prednames'][ii] == predname and csvv['covarnames'][ii] == covarname:
            return csvv['gamma'][ii]

    return None

def partial_derivative(csvv, covariate, covarunit):
    """Return a new CSVV object, which represents the coefficients that
    were interacted with the given covariate. Handles covariate terms defined
    as the product of multiple covariates."""

    covarnames = []
    include = []
    for ii in range(len(csvv['gamma'])):
        # Look for products
        m1 = re.search(r'\b' + covariate + r'\b\s*[*]\s*', csvv['covarnames'][ii])
        m2 = re.search(r'\s*[*]\s*\b' + covariate + r'\b', csvv['covarnames'][ii])
        if csvv['covarnames'][ii] == covariate: # Uninteracted covariate
            covarnames.append('1')
            include.append(True)
        elif m1:
            # The remaining covariate
            covarnames.append(re.sub(r'\b' + covariate + r'\b\s*[*]\s*', '', csvv['covarnames'][ii]))
            include.append(True)
        elif m2:
            covarnames.append(re.sub(r'\s*[*]\s*\b' + covariate + r'\b', '', csvv['covarnames'][ii]))
            include.append(True)
        else:
            include.append(False)
    csvvpart = subset(csvv, include)
    if 'outcome' in csvv['variables']:
        csvvpart['variables'] = csvvpart['variables'].copy()  # remove when MetaCSV fixed
        csvvpart['variables']._data = copy.deepcopy(csvvpart['variables']._data)
        oldunit = csvv['variables']['outcome']['unit']
        csvvpart['variables']['outcome']['unit'] = csvv['variables']['outcome']['unit'] + '/' + covarunit
        assert csvv['variables']['outcome']['unit'] == oldunit
    csvvpart['covarnames'] = covarnames

    # Make sure that we have a constant
    missing_prednames = []
    for predname in set(csvv['prednames']):
        found_constant = False
        for ii in range(len(csvvpart['prednames'])):
            if csvvpart['prednames'][ii] == predname and csvvpart['covarnames'][ii] == '1':
                found_constant = True
                break
        if not found_constant:
            missing_prednames.append(predname)

    if len(missing_prednames) > 0:
        csvvpart['prednames'] = np.append(csvvpart['prednames'], missing_prednames)
        csvvpart['covarnames'] = np.append(csvvpart['covarnames'], map(lambda x: '1', missing_prednames))
        csvvpart['gamma'] = np.append(csvvpart['gamma'], map(lambda x: 0, missing_prednames))
        # gammavcv already was collapsed, because we successfully called subset
    
    return csvvpart
