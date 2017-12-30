import csv, os
import numpy as np
from netCDF4 import Dataset
import nc4writer
from helpers import header
from datastore import irregions
from impactlab_tools.utils import files

def iterdir(basedir, dironly=False):
    for filename in os.listdir(basedir):
        if dironly and not os.path.isdir(os.path.join(basedir, filename)):
            continue
        yield filename, os.path.join(basedir, filename)

def iterresults(outdir, batchfilter=lambda batch: True, targetdirfilter=lambda targetdir: True):
    for batch, batchpath in iterdir(files.configpath(outdir), True):
        if not batchfilter(batch):
            continue
        for clim_scenario, cspath in iterdir(batchpath, True):
            for clim_model, cmpath in iterdir(cspath, True):
                for econ_model, empath in iterdir(cmpath, True):
                    for econ_scenario, espath in iterdir(empath, True):
                        if not targetdirfilter(espath):
                            continue
                        yield batch, clim_scenario, clim_model, econ_scenario, econ_model, espath

def copy_timereg_variable(writer, variable, key, dstvalues, suffix, unitchange=lambda x: x, timevar='year'):
    column = writer.createVariable(key, 'f8', (timevar, 'region'))
    if hasattr(variable, 'units'):
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
        elif (timevar, 'region') == reader.variables[key].dimensions[:2] and reader.variables[key].shape[2] == 1: # This is currently true of temps
            print key
            variable = reader.variables[key][:, :, 0]

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
    with open(files.sharedpath('regions/macro-regions.csv'), 'r') as fp:
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

def combine_results(targetdir, basename, sub_basenames, get_stweights, description, suffix=''):
    writer = nc4writer.create(targetdir, basename + suffix)

    sub_filepaths = [os.path.join(targetdir, sub_basename + '.nc4') for sub_basename in sub_basenames]
    readers = [Dataset(sub_filepath, 'r', format='NETCDF4') for sub_filepath in sub_filepaths]

    regions = readers[0].variables['regions'][:].tolist()
    for reader in readers[1:]:
        regions2 = reader.variables['regions'][:].tolist()
        if isinstance(regions[0], float) and isinstance(regions2[0], float) and np.isnan(regions[0]) and np.isnan(regions2[0]) and len(regions) == len(regions2):
            # Good enough of a check for us
            pass
        else:
            assert regions == regions2, "Regions do not match: %s <> %s" % (str(regions[:4]), str(regions2[:4]))

    if isinstance(regions[0], float) and np.isnan(regions[0]):
        dependencies = []
        regions = irregions.load_regions('hierarchy.csv', dependencies)

    try:
        writer.description = description
        writer.version = readers[0].version
        writer.dependencies = sub_filepaths
        writer.author = readers[0].author
    except:
        pass

    years = nc4writer.make_years_variable(writer)
    years[:] = nc4writer.get_years(readers[0])
    nc4writer.make_regions_variable(writer, regions, 'regions')

    stweights = [get_stweight(min(years), max(years)) for get_stweight in get_stweights]

    all_variables = {} # key -> list of variables
    for reader in readers:
        for key, variable in iter_timereg_variables(reader):
            if key not in all_variables:
                all_variables[key] = [variable]
            else:
                all_variables[key].append(variable)

    print {key: len(all_variables[key]) for key in all_variables}
                
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

def make_batchfilter(config):
    if 'batch' in config:
        return lambda batch: batch == config['batch']
    if 'mode' in config:
        if config['mode'] == 'median':
            return lambda batch: batch == 'median'
        elif config['mode'] == 'montecarlo':
            return lambda batch: batch[:5] == 'batch'
        elif config['mode'] == 'xsingle':
            return lambda batch: batch == 'median' or 'batch' in batch
        else:
            print "WARNING: Unknown mode %s" % config['mode']
    return lambda batch: True
            
def config_targetdirfilter(clim_scenario, clim_model, econ_scenario, econ_model, targetdir, config):
    if 'rcp' in config:
        if clim_scenario != config['rcp']:
            return False
    if 'gcm' in config:
        if clim_model != config['gcm']:
            return False
    if 'ssp' in config:
        if econ_scenario != config['ssp']:
            return False
    if 'iam' in config:
        if econ_model != config['iam']:
            return False
    if 'targetdir' in config:
        if targetdir != config['targetdir']:
            return False

    return True


            
