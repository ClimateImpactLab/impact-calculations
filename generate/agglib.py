import csv, os
import numpy as np
from netCDF4 import Dataset
from . import nc4writer
from helpers import header
from datastore import irregions
from impactlab_tools.utils import files
import re
from . import pvalses 
import collections 

def iterdir(basedir, dironly=False):
    """Generator giving filename, path for files and dirs within `basedir`.

    Parameters
    ----------
    basedir : str
        Target directory to iterate through.
    dironly : bool, optional
        Should directories be yielded?

    Yields
    ------
    filename : str
    path : str
    """
    for filename in os.listdir(basedir):
        if dironly and not os.path.isdir(os.path.join(basedir, filename)):
            continue
        yield filename, os.path.join(basedir, filename)

def iterresults(outdir, batchfilter=lambda batch: True, targetdirfilter=lambda targetdir: True):
    """Generator giving run info based on proj output director, after filtering

    Parameters
    ----------
    outdir : str
        Path to directory of impact projection output.
    batchfilter : Callable, optional
        Given batch information str arg, return bool indicating whether to
        include the batch. Default returns True for everything, i.e. no
        filtering.
    targetdirfilter : Callable, optional
        Given directory str arg, return bool indicating whether to
        include the target directory. Default returns True for everything,
        i.e. no filtering.

    Yields
    ------
    batch : str
    clim_scenario : str
    clim_model : str
    econ_scenario : str
    econ_model : str
    espath : str
    """
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
    """Creates a copy of the source variable, with the given aggregated data.

    This is called after we have already done the aggregation, to copy
    the result into the `writer` output file.

    Parameters
    ----------
    writer : NetCDF4.Dataset
        The target file; should already have dimensions defined.
    variable : NetCDF4.Variable
        The unaggregated variable, to copy metadata.
    key : str
        The name of the variable
    dstvalues : array_like
        A 2D matrix (time x region) containing the aggregated data.
    suffix : str
        Additional information to add to source metadata.
    unitchange : function(str), optional
        Transforms the original units to result units, if provided.
    timevar : str
        The name of the time dimension.
    """
    # Create the output variable
    column = writer.createVariable(key, 'f4', (timevar, 'region'))
    if hasattr(variable, 'units'):
        column.units = unitchange(variable.units)
    if hasattr(variable, 'long_title'):
        column.long_title = variable.long_title
    if hasattr(variable, 'source'):
        column.source = variable.source + " " + suffix

    column[:, :] = dstvalues

def iter_timereg_variables(reader, timevar='year', config=None):
    """Locates all variables that have time and region dimensions and can be aggregated.

    We can aggregate any variable that has dimensions (time x
    region). We also handle an old case where weather variables were
    stored as (time x region x singleton dimension).

    Parameters
    ----------
    reader : NetCDF4.Dataset
        The source for variables we want to process.
    timevar : str, optional
        The name of the time dimension.
    config : dict, optional
        The aggregation configuration dictionary

    Yields
    ------
    tuple(str, NetCDF4.Variable)
        Yields each variable we can process
    """
    if config == None:
        config = {}
    
    # Look through all variables
    for key in list(reader.variables.keys()):
        if key not in config.get('only-variables', [key]):
            continue
        
        if (timevar, 'region') == reader.variables[key].dimensions:
            # Yield this (time, region) variable
            print(key)
            variable = reader.variables[key]

            yield key, variable
        elif (timevar, 'region') == reader.variables[key].dimensions[:2] and reader.variables[key].shape[2] == 1: # This is currently true of temps
            # Yield this (time, region, singleton dimension) variable
            print(key)
            variable = reader.variables[key][:, :, 0]

            yield key, variable

def get_aggregated_regions(regions):
    """Returns all higher-level regions associated with IR list regions.

    This works by assuming that IR keys are named hierarchically, so
    the IR region "USA.16.208" is included in three aggregations: ""
    (the global aggregation), "USA" (country-level), and "USA.16"
    (state-level).

    We also include regions from the FUND model, as keys of the form
    FUND-key.

    Parameters
    ----------
    regions : sequence of str
        List of IR keys, like "USA.16.208"

    Returns
    -------
    tuple(dict, list, list)
        - The first item is a dictionary with a key for each
        aggregated region, associated with a list of a list of all
        contained IR keys.
        - The second item is a list of all identified aggregated
        region keys.
        - The third item is a list of dependencies, acquired in the
        process.

    """
    # Collect regions into lists at levels of aggregation
    originals = {} # { prefix: [region] }
    for region in regions:
        original = region
        if len(region) == 3:
            originals[region] = [region]
            continue # Add single-region countries

        # Iterate up the IR key structure, to get all levels
        while len(region) > 3:
            region = region[:region.rindex('.')]
            if region in originals:
                originals[region].append(original)
            else:
                originals[region] = [original]

    # Add the FUND regions
    dependencies = []
    with open(files.sharedpath('regions/macro-regions.csv'), 'r', encoding='ISO-8859-1') as fp:
        # Remove the metadata header
        aggreader = csv.reader(header.deparse(fp, dependencies))
        headrow = next(aggreader)
        for row in aggreader:
            # Each row gives the FUND region for each ISO3 country code
            fundregion = 'FUND-' + row[headrow.index('FUND')]
            if fundregion not in originals:
                originals[fundregion] = []

            iso3 = row[headrow.index('region-key')]
            if iso3 not in originals:
                continue

            originals[fundregion].extend(originals[iso3])

    # Collect all prefixes
    prefixes = [''] + list(originals.keys()) # '' = world

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
    except Exception as ex:
        print("Exception raised, passing:")
        print(ex)
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

    print({key: len(all_variables[key]) for key in all_variables})

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
    """Parse config dict mode to return callable 'batchfilter'

    This 'batchfilter' takes a single arg, most likely a str, and outputs
    boolean, depending on whether the str matches config.mode or not.

    If 'mode' and 'batch' not in `config`, then return a callable simply
    returning `True`.

    Parameters
    ----------
    config : dict
        A configuration dictionary.

    Returns
    -------
    Callable
        A 'batchfilter'.
    """
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
            print("WARNING: Unknown mode %s" % config['mode'])
    return lambda batch: True

def config_targetdirfilter(clim_scenario, clim_model, econ_scenario, econ_model, targetdir, config):
    """Given run information, test if matches info in run config

    Parameters
    ----------
    clim_scenario : str
    clim_model : str
    econ_scenario : str
    econ_model : str
    targetdir : str
        Path to target directory.
    config : dict

    Returns
    -------
    bool
    """
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

def get_farmer_suffix(filename):
    """Return the 'incadapt', 'noadapt', 'histclim', 'incadapt-histclim', 'noadapt-histclim' suffix if there or '' if not."""
    parts = filename.split('-')
    if parts[-1] == 'histclim.nc4' and len(parts) > 1 and parts[-2] in ['incadapt', 'noadapt']:
        return parts[-2] + '-histclim'
    if parts[-1] in ['incadapt.nc4', 'noadapt.nc4', 'histclim.nc4']:
        return parts[-1][:-4]
    return ''

def available_cost_use_args():
    """ returns a list of str containing known 'use-args' interpretable by interpret_cost_use_args()  """
    return ['clim_scenario', 'clim_model', 'impactspath', 'batchwd', 'ssp_num','rcp_num','iam','seed-csvv', 'costs-suffix']

def interpret_cost_use_args(use_args, outputdir, targetdir, batch, clim_scenario, clim_model,econ_model, econ_scenario, filename, costs_suffix):
    """retrieves arguments for a cost script among a known set of arguments using some directory information. 
    Availability definition in `available_cost_args()` should be updated as needed. 

    Parameters
    ----------
    use_args : list of str
    outputdir : str
    targetdir : str
    batch : str
    clim_scenario : str
    clim_model : str
    econ_scenario : str
    econ_model : str
    filename : str
        used to be returned as such with its path and to retrieve `pvals.yml` if needed
    costs_suffix : str

    Returns 
    -------
    a list containing arguments selected by `use_args`. 
    """

    available_args = {'clim_scenario' : clim_scenario,
    'clim_model' : clim_model,
    'impactspath' : os.path.join(targetdir, filename),
    'batchwd' : os.path.join(outputdir,batch),
    'ssp_num' : re.sub('\D', '', econ_scenario),
    'rcp_num' : re.sub('\D', '', clim_scenario),
    'iam' : econ_model,
    'costs-suffix' : costs_suffix}

    if 'seed-csvv' in use_args:
        available_args['seed-csvv']=str(pvalses.read_pval_file(path=os.path.join(outputdir, targetdir), relative_location=targetdir)[filename[:-4]]['seed-csvv'])

    return [available_args[x] for x in use_args]
 
def interpret_cost_args(costs_script, **targetdir_info):

    """interprets and collects cost-script arguments, preserving the order defined by the user.  
    Able to pick and understands only 'use-args' and 'extra-args' keys. 

    Parameters
    ----------
    costs_script : dict. 
        Must contain the following keys : 
            'costs-suffix' str 
            'ordered-args' collections.OrderedDict. Known keys :
                'use-args' list of str.
                'extra-args' dict
    **targetdir_info : additional arguments passed on to interpret_cost_use_args()

    Returns 
    -------
    list of str containing all the arguments to be concatenated and passed to the costs script.
    """

    arglist = list() # initialize

    ordered_args = costs_script.get('ordered-args')
    for argtype in ordered_args:

        if argtype=='use-args':
            arglist = arglist + interpret_cost_use_args(use_args=ordered_args['use-args'], 
                                                        **targetdir_info)
        elif argtype=='extra-args':
            arglist = arglist + [str(x) for x in list(ordered_args['extra-args'].values())]
        else: 
            raise ValueError('unknown argtype in the costs script `ordered-args`. Should contain either `use-args` or `extra-args` or both')

    return arglist

def get_meta_info_costs(name):


    if name not in ['deaths', 'yields']:
        raise ValueError('unknown identifier of meta information for costs netcdfs')
    data = {'deaths': dict(description="Upper and lower bounds costs of adaptation calculation.",
                    version="DEADLY-2016-04-22",
                    dependencies="TEMPERATURES, ADAPTATION-ALL-AGES",
                    author="Tamma Carleton"), 
    'yields': dict(description="costs of yield adaptation to temperature and precipitation long term changes",
                    version="YIELDS-2021-06-03",
                    dependencies="tmp_and_prcp_costs.R",
                    author="Andy Hultgren")}

    return data[name]

def interpret_costs_script(costs_script):

    """ interprets the `costs-script` entry of an aggregator config and verifies that required 
    entries are present.

    Returns
    -------
    a list of str containing possible etnries to the `costs_script` config key : 
    [command_prefix, ordered_args, use_args, extra_args, costs_suffix, costs_variable]
    
    """

    command_prefix = costs_script.get('command-prefix', None)
    ordered_args = collections.OrderedDict(costs_script.get('ordered-args')) if costs_script.get('ordered-args', None) is not None else None 
    if ordered_args is None or (ordered_args.get('use-args', None) is None and ordered_args.get('extra-args', None) is None):
        raise ValueError('user must pass an `ordered_args` dictionary containing either `extra-args` or `use-args` keys')
    use_args = costs_script.get('use-args', None)
    extra_args = costs_script.get('extra-args', None)
    costs_suffix = costs_script.get('costs-suffix', None) # if starts with '-', interpreted as suffix, otherwise as full file name.
    costs_variable = costs_script.get('check-variable-costs', None)
    if command_prefix is None or costs_suffix is None or costs_variable is None or costs_script.get('description', None) is None :
        raise ValueError('missing info in costs-script dictionary')
    if use_args is not None and not all(arg in agglib.available_cost_use_args() for arg in use_args):
        raise ValueError('unknown entries in `use-args` for costs')

    return [command_prefix, ordered_args, use_args, extra_args, costs_suffix, costs_variable]

