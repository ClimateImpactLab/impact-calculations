"""
Various utils for various sector-specific diagnostic scripts.
"""

import csv
import os
import subprocess

import numpy as np
from netCDF4 import Dataset


def show_header(text):
    """Pretty printing of str `text`
    """
    print "\n\033[1m" + text + "\033[0m"


def show_julia(command, clipto=160):
    """Print output from running command in Julia
    """
    if isinstance(command, str):
        print command
        print "# " + subprocess.check_output(["julia", "-e", "println(" + command + ")"])
    else:
        for line in command:
            if clipto is not None and len(line) > clipto:
                print line[:(clipto-3)] + '...'
            else:
                print line

        print "# " + subprocess.check_output(
            ["julia", "-e", "; ".join(command[:-1]) + "; println(" + command[-1] + ")"])


def get_excerpt(filepath, first_col, regionid, years, hasmodel=True, onlymodel=None, hidecols=None):
    """
    Get section of projection diagnostic output CSV file

    Parameters
    ----------
    filepath : str
        Path to target file.
    first_col : int
        0 based index for the column at which data actually starts, following
        "region", "year", and possibly "model"(s) columns.
    regionid : str
        Year to extract from CSV file. Parsed from the first column.
    years : sequence
        Sequence of years to extract from CSV file.
    hasmodel : bool, optional
        Does the file have columns for models?
    onlymodel : str or None, optional
        Which models should be subset from the file. Only works if there is
        a "models" column in the file index. If None, then no subset is
        extracted, or no models information is included in the file.
    hidecols : sequence of str or None, optional
        Columns in the target file to exclude from the returned data. If None,
        no columns are hidden.

    Returns
    -------
    out : dict
        A dictionary with keys for every year in the target file and a "header"
        key. "header" contains a list of str, giving an ordered sequence of
        columns. The elements with year keys are lists containing floats and
        potentially ``np.nan``. Note that the year indices are str. The order
        of the items in this list correspond to the order in
        ``out['header']]``.
    """
    if hidecols is None:
        hidecols = []

    data = {}
    model = None
    with open(filepath, 'r') as fp:
        for line in fp:
            if line.rstrip() == '...':
                break
        reader = csv.reader(fp)
        header = reader.next()
        data['header'] = header[first_col:]
        # Find columns to hide
        showcols = np.array([col not in hidecols for col in header])
        
        print ','.join(np.array(header)[showcols])
        print "..."
        for row in reader:
            if 'e+06' in row[1]:
                row[1] = str(int(float(row[1]) / 1000))
            if '.' in row[1]:
                row[1] = str(int(float(row[1])))
            if row[0] == regionid and row[1] in map(str, years):
                if hasmodel:
                    if onlymodel is not None and row[2] != onlymodel:
                        continue
                    if model is None:
                        model = row[2]
                    elif model != row[2]:
                        break
                print ','.join(np.array(row)[showcols[:len(row)]])
                if int(row[1]) + 1 not in years:
                    print "..."
                if row[1] in data:
                    # Just fill in NAs (until we figure out why dubling up lines)
                    for ii in range(len(data[row[1]])):
                        if np.isnan(data[row[1]][ii]):
                            data[row[1]][ii] = float(row[first_col+ii])
                else:
                    data[row[1]] = map(lambda x: float(x) if x != 'NA' else np.nan, row[first_col:])

    return data


def excind(data, year, column):
    """
    Extract a year and column from a data dict.

    Parameters
    ----------
    data : dict
        A dictionary as output from ``get_excerpt``. Needs a "header" element,
        and all other values are indexed on str keys giving the years of
        data.
    year : str
        Year to extract. Must be in `data`.
    column : str
        'Column' from ``data`` to extract.
    """
    return data[str(year)][data['header'].index(column)]


def parse_csvv_line(line):
    line = line.rstrip().split(',')
    if len(line) == 1:
        line = line[0].split('\t')

    return line


def get_csvv(filepath, index0=None, indexend=None):
    """
    Read CSVV file and return contents

    Parameters
    ----------
    filepath : str
        Path to target CSVV file.
    index0 : int or None, optional
        First value of slice to select a subset of elements from the file
        line.
    indexend : int or None, optional
        Second value of slice to select a subset of elements from the file
        line.

    Returns
    -------
    csvv : dict
        Dictionary representing the content of a CSVV file. Keys give file
        field names.
    """
    csvv = {}
    with open(filepath, 'rU') as fp:
        printline = None
        for line in fp:
            if printline is not None:
                if printline == 'gamma':
                    csvv['gamma'] = map(float, parse_csvv_line(line))
                else:
                    csvv[printline] = map(lambda x: x.strip(), parse_csvv_line(line))

                if index0 is not None:
                    csvv[printline] = csvv[printline][index0:indexend]
                print ','.join(map(str, csvv[printline]))
                    
                printline = None
            if line.rstrip() in ["prednames", "covarnames", "gamma"]:
                printline = line.rstrip()

    return csvv


def get_gamma(csvv, predname, covarname):
    """Get gamma values from a CSVV dict.

    Parameters
    ----------
    csvv : dict
        CSVV values as returned from ``get_csvv``
    predname : str
        Extract value corresponding to "predname".
    covarname : str
        Extract value corresponding to "covarname".
    """
    for ii in range(len(csvv['gamma'])):
        if csvv['prednames'][ii] == predname and csvv['covarnames'][ii] == covarname:
            return csvv['gamma'][ii]

    return None


def show_coefficient(csvv, preds, year, coefname, covartrans, calconly=False):
    """
    Extract coefficient from CSVV and do some calculations in Julia with it.

    Parameters
    ----------
    csvv : dict
        CSVV data, as output from get_CSVV.
    preds : dict
        A dictionary as output from ``get_excerpt``. Needs a "header" element,
        and all other values are indexed on str keys giving the years of
        data.
    year : int
        Target year to calculate for.
    coefname : str
        Name of coefficient listed in ``csvv['prednames']`` to work from.
    covartrans : dict
        Covariate transformations dictionary. Time has long forgotten what this
        actually does. But it does do something.
    calconly : bool, optional
        If True, simply return a str showing the julia calculation, otherwise
        the calculation is run and printed to stdout.

    Returns
    -------
    str is returned if `calconly is True. Otherwise has the sideeffect of
    triggering a calculation in Julia.
    """
    predyear = year - 1 if year > 2015 else year

    terms = []
    for ii in range(len(csvv['gamma'])):
        if csvv['prednames'][ii] == coefname:
            if csvv['covarnames'][ii] == '1':
                terms.append(str(csvv['gamma'][ii]))
            elif csvv['covarnames'][ii] in covartrans:
                if covartrans[csvv['covarnames'][ii]] is None:
                    continue  # Skip this one
                terms.append(
                    str(csvv['gamma'][ii]) + " * " + str(excind(preds, predyear, covartrans[csvv['covarnames'][ii]])))
            else:
                terms.append(str(csvv['gamma'][ii]) + " * " + str(excind(preds, predyear, csvv['covarnames'][ii])))

    if calconly:
        return ' + '.join(terms)
    
    show_julia(' + '.join(terms))


def show_coefficient_mle(csvv, preds, year, coefname, covartrans):
    predyear = year - 1 if year > 2015 else year

    terms = []
    for ii in range(len(csvv['gamma'])):
        if csvv['prednames'][ii] == coefname:
            if csvv['covarnames'][ii] == '1':
                continue
            elif csvv['covarnames'][ii] in covartrans:
                terms.append(
                    str(csvv['gamma'][ii]) + " * " + str(excind(preds, predyear, covartrans[csvv['covarnames'][ii]])))
            else:
                terms.append(str(csvv['gamma'][ii]) + " * " + str(excind(preds, predyear, csvv['covarnames'][ii])))

    beta = [csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if
            csvv['prednames'][ii] == coefname and csvv['covarnames'][ii] == '1'][0]

    show_julia("%f * exp(%s)" % (beta, ' + '.join(terms)))


def get_regionindex(region):
    with open("/shares/gcp/regions/hierarchy.csv", 'r') as fp:
        for line in fp:
            if line[0] != '#':
                break

        reader = csv.reader(fp)
        for row in reader:
            if row[0] == region:
                return int(row[6]) - 1


def get_adm0_regionindices(adm0):
    with open("/shares/gcp/regions/hierarchy.csv", 'r') as fp:
        for line in fp:
            if line[0] != '#':
                break

        reader = csv.reader(fp)
        for row in reader:
            if row[0][:3] == adm0 and row[6] != '':
                yield int(row[6]) - 1


def get_weather(weathertemplate, years, shapenum=None, show_all_years=[], variable='tas'):
    """Extract a subset of weather from a NetCDF4 file.

    Parameters
    ----------
    weathertemplate : str
        A str with replacement fields for ''{rcp}'', ''{variable}'', and
        ''{year}''.
    years : sequence
        Sequence of years to extract.
    shapenum : str, int, or None, optional
        If str, `shapenum` is treated as a region and this region is extracted
        from the target file. Otherwise, used to extract from the last
        dimension of the data variable.
    show_all_years : sequence of str, optional
        Print debug information for these select years. Default prints nothing.
    variable : str, optional
        Variable to extract from target NetCDF file.

    Returns
    -------
    weather : dict
        Data extracted from target NetCDF file. Dictionary keys are ints giving
        extracted years. Dictionary values are numpy.ndarray.
    """
    weather = {}
    for year in years:
        filepath = weathertemplate.format(rcp='historical' if year < 2006 else 'rcp85', variable=variable, year=year)
        assert os.path.exists(filepath), "Cannot find %s" % filepath
        rootgrp = Dataset(filepath, 'r', format='NETCDF4')
        if isinstance(shapenum, str):
            regions = rootgrp.variables['hierid'][:]
            regions = [''.join([region[ii] for ii in range(len(region)) if region[ii] is not np.ma.masked]) for region
                       in regions]
            shapenum = regions.index(shapenum)

        if len(rootgrp.variables[variable].shape) == 2:
            data = rootgrp.variables[variable][:, shapenum]
        else:
            data = rootgrp.variables[variable][shapenum]

        if len(rootgrp.variables[variable].shape) == 2:
            if year in show_all_years:
                print str(year) + ': ' + ','.join(map(str, data))
            else:
                print str(year) + ': ' + ','.join(map(str, data[:10])) + '...'
        else:
            print "%d: %f" % (year, data)
            
        weather[year] = data
        rootgrp.close()

    return weather


def get_outputs(outputpath, years, shapenum, timevar='year'):
    """Read and subset

    Parameters
    ----------
    outputpath : str
        Path to output projection NetCDF4 file.
    years : sequence of int
        Years to extract from the target file.
    shapenum : str, int, or None, optional
        If str, `shapenum` is treated as a region and this region is extracted
        from the target file. Otherwise, used to extract from the last
        dimension of the data variable.
    timevar : str, optional
        Name of the "time" variable.

    Returns
    -------
    outputs : dict of dicts
        Data extracted from the projection NetCDF4 file. Keys to this dict
        give years (as int) from the file, and values are nested dicts like:
        {variable: value}.
    """
    rootgrp = Dataset(outputpath, 'r', format='NETCDF4')
    if isinstance(shapenum, str):
        regions = list(rootgrp.variables['regions'][:])
        shapenum = regions.index(shapenum)

    outyears = list(rootgrp.variables[timevar])
    outvars = [var for var in rootgrp.variables if len(rootgrp.variables[var].shape) == 2]
    print 'year,' + ','.join(outvars)
    
    outputs = {}
    for year in years:
        data = {var: rootgrp.variables[var][outyears.index(year), shapenum] for var in outvars}
        outputs[year] = data
        
        print ','.join([str(year)] + [str(data[var]) for var in outvars])

    return outputs
