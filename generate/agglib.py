import csv, os
import numpy as np
from netCDF4 import Dataset
import nc4writer
from helpers import header

def copy_timereg_variable(writer, variable, key, dstvalues, suffix, unitchange=lambda x: x, timevar='year'):
    column = writer.createVariable(key, 'f8', (timevar, 'region'))
    column.units = unitchange(variable.units)
    if hasattr(variable, 'long_title'):
        column.long_title = variable.long_title
    if hasattr(variable, 'source'):
        column.source = variable.source + " " + suffix

    column[:, :] = dstvalues

def iter_timereg_variables(reader, timevar='year'):
    for key in reader.variables.keys():
        if (timevar, 'region') == reader.variables[key].dimensions:
            print key
            variable = reader.variables[key]

            yield key, variable

def get_aggregated_regions(regions):
    # Collect all levels of aggregation
    originals = {} # { prefix: [region] }
    for region in regions:
        original = region
        while len(region) > 3:
            region = region[:region.rindex('.')]
            if region in originals:
                originals[region].append(original)
            else:
                originals[region] = [original]

    # Add the FUND regions
    dependencies = []
    with open('/shares/gcp/regions/macro-regions.csv', 'r') as fp:
        aggreader = csv.reader(header.deparse(fp, dependencies))
        headrow = aggreader.next()
        for row in aggreader:
            fundregion = 'FUND-' + row[headrow.index('FUND')]
            if fundregion not in originals:
                originals[fundregion] = []

            iso3 = row[headrow.index('region-key')]
            if iso3 not in originals:
                continue

            originals[fundregion].extend(originals[iso3])

    # Collect all prefixes with > 1 region
    prefixes = [''] # '' = world
    for prefix in originals:
        if originals[prefix] > 1:
            prefixes.append(prefix)

    return originals, prefixes, dependencies

def get_years(reader, limityears=None):
    if 'year' in reader.variables:
        readeryears = reader.variables['year'][:]
    elif 'years' in reader.variables:
        readeryears = reader.variables['years'][:]
    else:
        raise RuntimeError("Cannot find years variable")

    if limityears is not None:
        readeryears = limityears(readeryears)

    if len(readeryears) == 0:
        raise ValueError("Incomplete!")

    return readeryears

def combine_results(targetdir, basename, sub_basenames, get_stweights, description, suffix=''):
    writer = nc4writer.create(targetdir, basename + suffix)

    sub_filepaths = [os.path.join(targetdir, sub_basename + '.nc4') for sub_basename in sub_basenames]
    readers = [Dataset(sub_filepath, 'r', format='NETCDF4') for sub_filepath in sub_filepaths]

    regions = readers[0].variables['regions'][:].tolist()
    for reader in readers[1:]:
        regions2 = reader.variables['regions'][:].tolist()
        assert regions == regions2, "Regions do not match."

    writer.description = description
    writer.version = readers[0].version
    writer.dependencies = sub_filepaths
    writer.author = readers[0].author

    years = nc4writer.make_years_variable(writer)
    years[:] = get_years(readers[0])
    nc4writer.make_regions_variable(writer, regions, 'regions')

    stweights = [get_stweight(min(years), max(years)) for get_stweight in get_stweights]

    all_variables = {} # key -> list of variables
    for reader in readers:
        for key, variable in iter_timereg_variables(reader):
            if key not in all_variables:
                all_variables[key] = [variable]
            else:
                all_variables[key].append(variable)

    for key in all_variables:
        if len(all_variables[key]) < len(readers):
            continue

        dstnumers = np.zeros((len(years), len(regions)))
        dstdenoms = np.zeros((len(years), len(regions)))        
        srcvalueses = [variable[:, :] for variable in all_variables[key]]
        for ii in range(len(regions)):
            for kk in range(len(readers)):
                weights = stweights[kk].get_time(regions[ii])
                if len(years) == len(weights) - 1:
                    weights = weights[:-1]
                dstnumers[:, ii] += srcvalueses[kk][:, ii] * weights
                dstdenoms[:, ii] += weights

        copy_timereg_variable(writer, all_variables[key][0], key, dstnumers / dstdenoms, "(combined)")

    for reader in readers:
        reader.close()
    writer.close()
