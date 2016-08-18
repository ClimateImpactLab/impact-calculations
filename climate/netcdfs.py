import os, re
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
    rootgrp = Dataset(filepath, 'r', format='NETCDF4')
    version = rootgrp.version
    units = rootgrp.variables[variable].units
    rootgrp.close()

    return version, units

def readncdf(filepath, variable):
    """
    Return yyyyddd, weather
    """
    rootgrp = Dataset(filepath, 'r', format='NETCDF4')
    weather = rootgrp.variables[variable][:,:]
    yyyyddd = rootgrp.variables['time'][:]
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
        return 'DayNumber'
    if filename[0:11] == 'number_days':
        return 'tas'
    if filename[0:6] in ['tasmin', 'tasmax']:
        return filename[0:6]
    if filename[0:3] == 'tas':
        return 'tas'
    if filename[0:2] == 'pr':
        return 'pr'

    return None

def iterate_bundles(basedir):
    """
    Return bundles for each RCP and model.

    basedir points to directory with both 'historical', 'rcp*'
    """
    # Collect the entire complement of models
    models = os.listdir(os.path.join(basedir, 'historical'))

    for scenario in os.listdir(basedir):
        if scenario[0:3] != 'rcp':
            continue

        for model in models:
            pasttemplate = os.path.join(basedir, 'historical', model, 'tas/tas_day_aggregated_historical_r1i1p1_' + model + '_%d.nc')
            futuretemplate = os.path.join(basedir, scenario, model, 'tas/tas_day_aggregated_' + scenario + '_r1i1p1_' + model + '_%d.nc')
            weatherbundle = UnivariatePastFutureWeatherBundle(pasttemplate, 1981, futuretemplate, 2006, 'tas')
            yield scenario, model, weatherbundle
