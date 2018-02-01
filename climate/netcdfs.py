import os, re
import numpy as np
from netCDF4 import Dataset

def get_arbitrary_variables(path):
    variables = {} # result of the function

    # Find all netcdfs within this directory
    for root, dirs, files in os.walk(path):
        for filename in files:
            # Check the filename
            match = re.match(r'.*?(pr|tasmin|tasmax|tas).*?\.nc', filename)
            if match:
                variable = match.group(1)
                filepath = os.path.join(root, filename)
                variables[variable] = filepath # add to the result set
                print "Found %s: %s" % (variable, filepath)

    return variables

def readmeta(filepath, variable):
    """
    Return version, units.
    """
    assert os.path.exists(filepath), filepath + " does not exist."

    rootgrp = Dataset(filepath, 'r', format='NETCDF4')
    assert variable in rootgrp.variables, "%s does not contain %s." % (filepath, variable)

    version = rootgrp.version
    if hasattr(rootgrp.variables[variable], 'units'):
        units = rootgrp.variables[variable].units
    else:
        units = rootgrp.variables[variable].unit
        
    rootgrp.close()

    return version, units

def readncdf(filepath, variable):
    """
    Return yyyyddd, weather
    """
    rootgrp = Dataset(filepath, 'r', format='NETCDF4')
    weather = rootgrp.variables[variable][:,:]
    if 'time' in rootgrp.variables:
        yyyyddd = rootgrp.variables['time'][:]
    else:
        yyyyddd = rootgrp.variables['day'][:]
    rootgrp.close()

    return yyyyddd, weather

def readncdf_single(filepath, variable, allow_missing=False):
    """
    Just return the variable
    """
    rootgrp = Dataset(filepath, 'r', format='NETCDF4')
    if allow_missing and variable not in rootgrp.variables:
        data = None
    else:
        data = np.copy(rootgrp.variables[variable])
    rootgrp.close()

    return data

def readncdf_multiple(filepath, variables):
    """
    Return yyyyddd, weather
    """
    rootgrp = Dataset(filepath, 'r', format='NETCDF4')
    if 'time' in rootgrp.variables:
        yyyyddd = rootgrp.variables['time'][:]
    else:
        yyyyddd = rootgrp.variables['day'][:]
        
    hierid = rootgrp.variables['hierid'][:]
    weather = np.empty(len(yyyyddd), len(hierid), len(variables))
    for ii in range(len(variables)):
        weather[:, :, ii] = rootgrp.variables[variables[ii]][:,:]
    rootgrp.close()

    return yyyyddd, weather

def readncdf_binned(filepath, variable):
    """
    Return month, perbin [12 x BINS x REGIONS]
    """

    rootgrp = Dataset(filepath, 'r', format='NETCDF4')
    weather = rootgrp.variables[variable][:,:,:]
    months = rootgrp.variables['month'][:]
    rootgrp.close()

    m = re.search('\\d{4}', filepath)
    if m:
        months = int(m.group(0)) * 1000 + months

    return months, weather

def available_years(template):
    """
    Returns the list of years available for a given template.
    Called with a template like the one used in WeatherBundle: `path/filename_%d.nc`
    """
    basedir, filetemplate = os.path.split(template)
    # Turn this into a regex
    filetemplate = filetemplate.replace('%d', '(\\d{4})')

    years = []
    for filename in os.listdir(basedir):
        m = re.match(filetemplate, filename)
        if m:
            years.append(int(m.group(1)))

    return years

def guess_historical(template):
    """
    Returns a plausible path to historical data.
    Called with a template like the one used in WeatherBundle: `path/filename_%d.nc`
    """
    scenarioindex = template.index('rcp')
    scenario = template[scenarioindex:scenarioindex+5]

    return template.replace(scenario, 'historical')

def guess_variable(filename):
    """
    Guess what the weather variable is from the filename.
    """
    if filename[0:7] == 'tas_day':
        return 'bintas'
    if filename[0:11] == 'number_days':
        return 'tas'
    if filename[0:6] in ['tasmin', 'tasmax']:
        return filename[0:6]
    if filename[0:3] == 'tas':
        return 'tas'
    if filename[0:2] == 'pr':
        return 'pr'

    return None
