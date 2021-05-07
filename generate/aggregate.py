"""Impact result aggregation tool.

See docs/aggregator.md for usage.

Code Organization
-----------------
This is the master script for performing aggregations. The main script
interprets an aggregation configuration file, and then iterates
through all of the available outputs in a specified directory
tree. The aggregation functions-- make_levels and make_aggregates,
along with make_costs_levels and make_costs_aggregates if a costs
script is used-- get run upon each output bundle.

Aggregation depends on weighting files, which are stored in
datastore/. The top-level classes for providing weighting information
are in datastore/spacetime.py. The translation process from
configuration file descriptions of weights to weighting object is
handled by datastore/weights.py.

Helper functions are organized in agglib.py, which are also used by
climateagg.py.
"""

import os, traceback
import numpy as np
from netCDF4 import Dataset
from . import nc4writer, agglib, checks
from datastore import weights
from impactlab_tools.utils import paralog

### Master Configuration
### See docs/aggregator.md for other configuration options

# Suffixes applied to the output filenames
costs_suffix = '-costs'   # adaptation costs file
levels_suffix = '-levels' # scaled results, typically changing rates to levels
suffix = "-aggregated"    # aggregated results across higher-level regions
missing_only = True       # generate only missing output files, or regenerate all?

debug_aggregate = False   # If not false, set to the name of an aggregated region to report. e.g., 'ARE'

# Command to run to generate adaptation costs files
costs_command = "Rscript generate/cost_curves.R \"%s\" \"%s\" \"%s\" \"%s\" \"%s\"" # tavgpath rcp gcm impactspath suffix

## Filters on target directories to aggregate

# batchfilter returns whether the batch directory should be processed
#   Process all batches: lambda batch: True
#   Ignore single directories: lambda batch: batch == 'median' or 'batch' in batch
batchfilter = lambda batch: True

# targetdirfilter returns whether the particular target directory should be processed
#   Process all target dirs: lambda targetdir: True
#   Only process RCP 8.5: lambda targetdir: 'rcp85' in targetdir
#   Only process SSP3: lambda targetdir: 'SSP3' in targetdir
targetdirfilter = lambda targetdir: True

# Future entry point
def main(config):
    raise NotImplementedError

## Cache of loaded weighting data
# Dictionary of (halfweight, weight_args, minyear, maxyear) => weights
cached_weights = {}

def get_cached_weight(halfweight, weight_args, years):
    """Return a `SpaceTimeData` object of weights with `get_time`, using
cached values as possible.

    Parameters
    ----------
    halfweight : `SpaceTimeData`
        A source for the weights, if the cache misses.
    weight_args : tuple
        Additional arguments to the `halfweight.load(y0, y1, ...)` function.
    years : sequence of int
        Years needed to be loaded.

    Returns
    -------
    `SpaceTimeData`
        A loaded object, either from the cache or from calling the
        `load` function on `halfweight`
    """
    global cached_weights

    # Get the full set of arguments
    minyear = int(min(years))
    maxyear = int(max(years))

    key = (halfweight, weight_args, minyear, maxyear)
    # Return the cached object, if available
    if key in cached_weights:
        return cached_weights[key]

    # Load weights; this may take a minute
    print("Loading weights...")
    stweight = halfweight.load(minyear, maxyear, *weight_args)
    print("Loaded.")

    # Save result to the cache
    cached_weights[key] = stweight
    return stweight

def make_aggregates(targetdir, filename, outfilename, halfweight, weight_args, dimensions_template=None, metainfo=None, limityears=None, halfweight_denom=None, weight_args_denom=None, config=None):
    """Generate aggregate output files.

    Creates a copy of the `targetdir/filename` NetCDF file as
    `targetdir/outfilename`, with higher-level regions aggregated
    according to the weights provided by `halfweight`.

    Handles regular and deltamethod files.

    Parameters
    ----------
    targetdir : str
        path to the target directory
    filename : str
        NetCDF filename within the target directory
    outfilename : str
        Filename for the resulting output
    halfweight : `SpaceTimeData`
        A source for the weights, if the cache misses.
    weight_args : tuple
        Additional arguments to the `halfweight.load(y0, y1, ...)` function.
    dimensions_template : str, optional
        Full path to a NetCDF file from which we want to take the dimensions information
    metainfo : dict, optional
        Overriding information for attributes; keys `description`, `version`, and `author` used.
    limityears : function(sequence of int), optional
        Filters the years extracted before returning.
    halfweight_denom : `SpaceTimeData`, optional
        An optional different source for denominator weights.
    weight_args_denom : tuple
        Additional arguments to the `halfweight_denom.load(y0, y1, ...)` function.
    config : dict, optional
        The aggregation configuration dictionary
    """
    # Read the source files
    reader = Dataset(os.path.join(targetdir, filename), 'r', format='NETCDF4')
    if dimensions_template is None:
        dimreader = reader
    else:
        dimreader = Dataset(dimensions_template, 'r', format='NETCDF4')

    # Set up the writer object
    writer = nc4writer.create(targetdir, outfilename)

    # Extract the years and regions
    readeryears = nc4writer.get_years(dimreader, limityears)

    regions = dimreader.variables['regions'][:].tolist()
    originals, prefixes, dependencies = agglib.get_aggregated_regions(regions)

    # Infer or collect metadata and copy it over
    if metainfo is None:
        writer.description = reader.description + " (aggregated)"
        writer.version = reader.version
        writer.dependencies = ', '.join(dependencies) + ', ' + reader.version
        writer.author = reader.author
    else:
        writer.description = metainfo['description']
        writer.version = metainfo['version']
        writer.dependencies = ', '.join(dependencies) + ', ' + metainfo['version']
        writer.author = metainfo['author']

    # Set up year and regions variables in result
    years = nc4writer.make_years_variable(writer)
    years[:] = readeryears

    nc4writer.make_regions_variable(writer, prefixes, 'aggregated')

    # Collect the weighting objects
    stweight = get_cached_weight(halfweight, weight_args, years)
    if halfweight_denom:
        if halfweight_denom == weights.HALFWEIGHT_SUMTO1: # singleton to force summing to 1
            stweight_denom = weights.HALFWEIGHT_SUMTO1
        else:
            stweight_denom = get_cached_weight(halfweight_denom, weight_args_denom, years)
    else:
        stweight_denom = None # Just use the same weight

    # If this is a deltamethod file, collect the VCV and setup in the output
    if 'vcv' in reader.variables:
        vcv = reader.variables['vcv'][:, :]
        writer.createDimension('coefficient', vcv.shape[0])
        vcvvar = writer.createVariable('vcv','f4',('coefficient', 'coefficient'))
        vcvvar[:, :] = vcv
    else:
        vcv = None

    # Convenience mapping from region key to index
    original_indices = {regions[ii]: ii for ii in range(len(regions))}

    # Iterate through all aggregatable variables
    for key, variable in agglib.iter_timereg_variables(reader, config=config):
        dstvalues = np.zeros((len(years), len(prefixes))) # output matrix
        dstvalues[:] = np.nan
        if vcv is None:
            srcvalues = variable[:, :]

            # Clean up bad values
            realvalues = np.isfinite(srcvalues)
            srcvalues = np.nan_to_num(srcvalues, copy=False, posinf=0, neginf=0)
            
            # Iterates over aggregated regions
            for ii in range(len(prefixes)):
                # Setup numerator and demoninator vector across time
                numers = np.zeros(srcvalues.shape[0])
                denoms = np.zeros(srcvalues.shape[0])

                # Get the list of regions we want to include in this aggregated region
                if prefixes[ii] == '':
                    # Special handling of '', the global region
                    withinregions = regions
                else:
                    withinregions = originals[prefixes[ii]]

                # Add each sub-region to the numerator and denominator
                for original in withinregions:
                    wws = np.array(stweight.get_time(original)) # Get vector of weights vs. time

                    if len(wws.shape) == 1 and wws.shape[0] != srcvalues.shape[0]:
                        # Shorten to the minimum of the two years
                        wws = wws[:min(wws.shape[0], srcvalues.shape[0])]
                        srcvalues = srcvalues[:min(wws.shape[0], srcvalues.shape[0]), :]
                        numers = numers[:srcvalues.shape[0]]
                        denoms = denoms[:srcvalues.shape[0]]

                    numers += wws * srcvalues[:, original_indices[original]]

                    if stweight_denom != weights.HALFWEIGHT_SUMTO1: # wait for sum-to-1
                        if stweight_denom:
                            weights_denom = stweight_denom.get_time(original)
                            denoms += weights_denom * realvalues[:, original_indices[original]]
                        else:
                            denoms += wws * realvalues[:, original_indices[original]]

                # Fill in result
                if stweight_denom == weights.HALFWEIGHT_SUMTO1: # wait for sum-to-1
                    dstvalues[:len(numers), ii] = numers
                else:
                    dstvalues[:len(numers), ii] = numers / denoms
        else:
            # Handle deltamethod files
            coeffvalues = np.zeros((vcv.shape[0], len(years), len(prefixes)))
            # Perform aggregation on BCDE vectors
            srcvalues = reader.variables[key + '_bcde'][:, :, :]

            # Clean up bad values
            realvalues = np.isfinite(srcvalues)
            srcvalues = np.nan_to_num(srcvalues, copy=False, posinf=0, neginf=0)

            # Iterates over aggregated regions
            for ii in range(len(prefixes)):
                # Setup numerator and demoninator vector across time
                numers = np.zeros(srcvalues.shape[:2]) # coeff, time
                denoms = np.zeros(srcvalues.shape[1]) # time

                # Get the list of regions we want to include in this aggregated region
                if prefixes[ii] == '':
                    # Special handling of '', the global region
                    withinregions = regions
                else:
                    withinregions = originals[prefixes[ii]]

                # Add each sub-region to the numerator and denominator
                for original in withinregions:
                    # Get vector of weights vs. time
                    wws = stweight.get_time(original)
                    if stweight_denom != weights.HALFWEIGHT_SUMTO1:
                        if stweight_denom:
                            weights_denom = stweight_denom.get_time(original)
                        else:
                            weights_denom = wws
                            
                    # Handle each year separately
                    for tt in range(len(years)):
                        if prefixes[ii] == debug_aggregate and tt == len(years) - 1:
                            print(original, wws[tt])
                            print(srcvalues[:, tt, original_indices[original]] * np.all(realvalues[:, tt, original_indices[original]]))
                        numers[:, tt] += wws[tt] * srcvalues[:, tt, original_indices[original]] * np.all(realvalues[:, tt, original_indices[original]])
                        if stweight_denom != weights.HALFWEIGHT_SUMTO1: # wait for sum-to-1
                            if prefixes[ii] == debug_aggregate and tt == len(years) - 1:
                                print(weights_denom[tt] * np.all(realvalues[:, tt, original_indices[original]]))
                            denoms[tt] += weights_denom[tt] * np.all(realvalues[:, tt, original_indices[original]])

                # Fill in result
                if stweight_denom == weights.HALFWEIGHT_SUMTO1: # wait for sum-to-1
                    coeffvalues[:, :, ii] = numers
                    if prefixes[ii] == debug_aggregate:
                        print("Numerators")
                        print(numers[:, len(years) - 1])
                else:
                    for tt in range(len(years)):
                        coeffvalues[:, tt, ii] = numers[:, tt] / denoms[tt]
                        if prefixes[ii] == debug_aggregate and tt == len(years) - 1:
                            print("Numerators / Denominators")
                            print(numers[:, tt])
                            print(numers[:, tt] / denoms[tt])
                # Now that we have the BCDE vectors, generate the new variance results
                for tt in range(len(years)):
                    dstvalues[tt, ii] = vcv.dot(coeffvalues[:, tt, ii]).dot(coeffvalues[:, tt, ii])
                    if prefixes[ii] == debug_aggregate and tt == len(years) - 1:
                        print(dstvalues[tt, ii])

            # We have to specifically create this, since the key was just the variance version
            coeffcolumn = writer.createVariable(key + '_bcde', 'f4', ('coefficient', 'year', 'region'))
            coeffcolumn[:, :, :] = coeffvalues

        # Copy the result into the output file
        agglib.copy_timereg_variable(writer, variable, key, dstvalues, "(aggregated)", unitchange=lambda unit: unit + '/person')

    # Close all files
    reader.close()
    if dimensions_template is not None:
        dimreader.close()
    writer.close()

def make_costs_aggregate(targetdir, filename, outfilename, halfweight, weight_args, halfweight_denom=None, weight_args_denom=None, config=None):
    """Aggregate adaptation costs (currently only for mortality).

    This sets up metadata appropriate to the mortality costs
    aggregation, and then calls `make_aggregates` for processing.

    Parameters
    ----------
    targetdir : str
        path to the target directory
    filename : str
        NetCDF filename within the target directory
    outfilename : str
        Filename for the resulting output
    halfweight : `SpaceTimeData`
        A source for the weights, if the cache misses.
    weight_args : tuple
        Additional arguments to the `halfweight.load(y0, y1, ...)` function.
    halfweight_denom : `SpaceTimeData`, optional
        An optional different source for denominator weights.
    weight_args_denom : tuple
        Additional arguments to the `halfweight_denom.load(y0, y1, ...)` function.
    config : dict, optional
        The aggregation configuration dictionary
    """
    # Setup the metadata
    dimensions_template = "/shares/gcp/outputs/temps/rcp45/CCSM4/climtas.nc4"
    metainfo = dict(description="Upper and lower bounds costs of adaptation calculation.",
                    version="DEADLY-2016-04-22",
                    dependencies="TEMPERATURES, ADAPTATION-ALL-AGES",
                    author="Tamma Carleton")

    # Perform the aggregation
    make_aggregates(targetdir, filename, outfilename, halfweight, weight_args, dimensions_template=dimensions_template, metainfo=metainfo, halfweight_denom=halfweight_denom, weight_args_denom=weight_args_denom, config=config)

def make_levels(targetdir, filename, outfilename, halfweight, weight_args, dimensions_template=None, metainfo=None, limityears=None, config=None):
    """Generate levels output files.

    Creates a copy of the `targetdir/filename` NetCDF file as
    `targetdir/outfilename`, with each result multiplied by a
    region-specific weight provided by `halfweight`.

    Handles regular and deltamethod files.

    Parameters
    ----------
    targetdir : str
        path to the target directory
    filename : str
        NetCDF filename within the target directory
    outfilename : str
        Filename for the resulting output
    halfweight : `SpaceTimeData`
        A source for the weights, if the cache misses.
    weight_args : tuple
        Additional arguments to the `halfweight.load(y0, y1, ...)` function.
    dimensions_template : str, optional
        Full path to a NetCDF file from which we want to take the dimensions information
    metainfo : dict, optional
        Overriding information for attributes; keys `description`, `version`, and `author` used.
    limityears : function(sequence of int), optional
        Filters the years extracted before returning.
    config : dict, optional
        The aggregation configuration dictionary
    """
    # Read the source files
    reader = Dataset(os.path.join(targetdir, filename), 'r', format='NETCDF4')
    if dimensions_template is None:
        dimreader = reader
    else:
        dimreader = Dataset(dimensions_template, 'r', format='NETCDF4')

    # Set up the writer object    
    writer = nc4writer.create(targetdir, outfilename)

    # Extract the years and regions
    years = nc4writer.make_years_variable(writer)
    years[:] = nc4writer.get_years(dimreader, limityears)

    regions = dimreader.variables['regions'][:].tolist()
    nc4writer.make_regions_variable(writer, regions, 'regions')

    # Infer or collect metadata and copy it over
    if metainfo is None:
        writer.description = reader.description + " (levels)"
        writer.version = reader.version
        writer.dependencies = reader.version
        writer.author = reader.author
    else:
        writer.description = metainfo['description']
        writer.version = metainfo['version']
        writer.dependencies = metainfo['version']
        writer.author = metainfo['author']

    # Construct the weighting object
    stweight = get_cached_weight(halfweight, weight_args, years)

    # If this is a deltamethod file, collect the VCV and setup in the output
    if 'vcv' in reader.variables:
        vcv = reader.variables['vcv'][:, :]
        writer.createDimension('coefficient', vcv.shape[0])
        vcvvar = writer.createVariable('vcv','f4',('coefficient', 'coefficient'))
        vcvvar[:, :] = vcv
    else:
        vcv = None
        
    # Iterate through all regional variables
    for key, variable in agglib.iter_timereg_variables(reader, config=config):
        dstvalues = np.zeros((len(years), len(regions))) # output matrix
        dstvalues[:] = np.nan
        if vcv is None:
            # Multiply each entry by appropriate weight   
            srcvalues = np.array(variable[:, :])
                
            for ii in range(len(regions)):
                wws = np.array(stweight.get_time(regions[ii]))

                if len(wws.shape) == 1 and wws.shape[0] != dstvalues.shape[0]:
                    # Shorten to the minimum of the two years
                    wws = wws[:min(wws.shape[0], srcvalues.shape[0])]
                    srcvalues = srcvalues[:min(wws.shape[0], srcvalues.shape[0]), :]
                    dstvalues[:len(wws), ii] = wws * srcvalues[:, ii]
                else:
                    dstvalues[:, ii] = wws * srcvalues[:, ii]
        else:
            # Handle deltamethod files
            coeffvalues = np.zeros((vcv.shape[0], len(years), len(regions)))
            # Perform multiplication on BCDE vectors
            srcvalues = reader.variables[key + '_bcde'][:, :, :]
            # Iterates over regions
            for ii in range(len(regions)):
                wws = stweight.get_time(regions[ii])
                for tt in range(len(years)):
                    # Generate both the BCDE values and the variances
                    coeffvalues[:, tt, ii] = srcvalues[:, tt, ii] * wws[tt]
                    dstvalues[tt, ii] = vcv.dot(coeffvalues[:, tt, ii]).dot(coeffvalues[:, tt, ii])

            # We have to specifically create this, since the key was just the variance version
            coeffcolumn = writer.createVariable(key + '_bcde', 'f4', ('coefficient', 'year', 'region'))
            coeffcolumn[:, :, :] = coeffvalues

        # Copy the result into the output file
        agglib.copy_timereg_variable(writer, variable, key, dstvalues, "(levels)", unitchange=lambda unit: unit.replace('/person', ''))

    # Close all files
    reader.close()
    if dimensions_template is not None:
        dimreader.close()
    writer.close()

def make_costs_levels(targetdir, filename, outfilename, halfweight, weight_args, config=None):
    """Make adaptation cost levels (currently only for mortality).

    This sets up metadata appropriate to the mortality costs levels
    calculation, and then calls `make_costs` for processing.

    Parameters
    ----------
    targetdir : str
        path to the target directory
    filename : str
        NetCDF filename within the target directory
    outfilename : str
        Filename for the resulting output
    halfweight : `SpaceTimeData`
        A source for the weights, if the cache misses.
    weight_args : tuple
        Additional arguments to the `halfweight.load(y0, y1, ...)` function.
    config : dict, optional
        The aggregation configuration dictionary
    """
    # Setup the metadata
    dimensions_template = "/shares/gcp/outputs/temps/rcp45/CCSM4/climtas.nc4"
    metainfo = dict(description="Upper and lower bounds costs of adaptation calculation.",
                    version="DEADLY-2016-04-22",
                    dependencies="TEMPERATURES, ADAPTATION-ALL-AGES",
                    author="Tamma Carleton")

    # Perform the levels calculations
    make_levels(targetdir, filename, outfilename, halfweight, weight_args, dimensions_template=dimensions_template, metainfo=metainfo, config=config)

def fullfile(filename, suffix, config):
    """Convenience function, to add config infix as needed to final filename."""
    if 'infix' in config:
        return fullfile(filename, '-' + str(config['infix']) + suffix, {})

    return filename[:-4] + suffix + '.nc4'
    
if __name__ == '__main__':
    # Prepare environment
    import sys
    from pathlib import Path
    from impactlab_tools.utils import files
    from interpret.configs import merge_import_config
    from datastore import population, agecohorts

    config = files.get_allargv_config()
    config_path = Path(sys.argv[1])
    # Interpret "import" in configs here while we have file path info.
    file_configs = merge_import_config(config, config_path.parent)

    regioncount = config.get('region-count', 24378) # used by checks to ensure complete files

    # Construct object to claim directories
    # Allow directories to be re-claimed after this many seconds
    claim_timeout = config.get('timeout', 24) * 60*60

    statman = paralog.StatusManager('aggregate', "generate.aggregate " + sys.argv[1], 'logs', claim_timeout)

    ### Determine weights
    
    if 'weighting' in config:
        # Same weighting for levels and aggregate
        halfweight_levels = weights.interpret_halfweight(config['weighting'])
        halfweight_aggregate = halfweight_levels
        halfweight_aggregate_denom = None # Same as numerator
        assert 'levels-weighting' not in config, "Cannot have both a weighting and levels-weighting option."
        assert 'aggregate-weighting' not in config, "Cannot have both a weighting and aggregate-weighting option."
        assert 'aggregate-weighting-numerator' not in config, "Cannot have both a weighting and aggregate-weighting-numerator option."
    else:
        # Levels weighting
        if 'levels-weighting' in config:
            halfweight_levels = weights.interpret_halfweight(config['levels-weighting'])
        else:
            halfweight_levels = None

        # Aggregate weighting
        if 'aggregate-weighting' in config:
            halfweight_aggregate = weights.interpret_halfweight(config['aggregate-weighting'])
            halfweight_aggregate_denom = None # Same as numerator
            assert 'aggregate-weighting-numerator' not in config, "Cannot have both a aggregate-weighting and aggregate-weighting-numerator option."
        else:
            # Separate numerator and denominator
            if 'aggregate-weighting-numerator' in config:
                halfweight_aggregate = weights.interpret_halfweight(config['aggregate-weighting-numerator'])
                halfweight_aggregate_denom = weights.interpret_halfweight(config['aggregate-weighting-denominator'])
            else:
                halfweight_aggregate = None
                halfweight_aggregate_denom = None

    ### Generate aggregate and levels files
                
    # Find all target directories
    for batch, clim_scenario, clim_model, econ_scenario, econ_model, targetdir in agglib.iterresults(config['outputdir'], agglib.make_batchfilter(config), targetdirfilter):
        # Check if we should process this targetdir
        if not agglib.config_targetdirfilter(clim_scenario, clim_model, econ_scenario, econ_model, targetdir, config):
            continue
        
        print(targetdir)
        print(econ_model, econ_scenario)

        # Try to claim the directory
        if not isinstance(debug_aggregate, str) and not statman.claim(targetdir) and 'targetdir' not in config:
            continue

        # Flag to be set true if could not do a complete aggregation
        incomplete = False
        if isinstance(debug_aggregate, str):
            incomplete = True

        # Try to process every NetCDF file in targetdir
        for filename in os.listdir(targetdir):
            if filename[-4:] == '.nc4' and suffix not in filename and costs_suffix not in filename and levels_suffix not in filename:
                if 'basename' in config:
                    if config['basename'] not in filename[:-4]:
                        continue

                if 'only-farmers' in config:
                    adaptsuffix = agglib.get_farmer_suffix(filename)
                    if adaptsuffix not in config['only-farmers']:
                        continue
                    
                # This looks like a valid file to consider!
                print(filename)

                # Check if this file is complete
                variable = config.get('check-variable', 'rebased')
                if not checks.check_result_100years(os.path.join(targetdir, filename), variable=variable, regioncount=regioncount):
                    print("Incomplete.")
                    incomplete = True
                    continue

                # Construct the weight arguments, inferring an age cohort if it's used
                if 'weighting' in config and config['weighting'] == 'agecohorts':
                    weight_args_levels = (econ_model, econ_scenario, agecohorts.age_from_filename(filename) if 'IND_' not in filename else 'total')
                    weight_args_aggregate = weight_args_levels
                    weight_args_aggregate_denom = None
                else:
                    if 'levels-weighting' in config and config['levels-weighting'] == 'agecohorts':
                        weight_args_levels = (econ_model, econ_scenario, agecohorts.age_from_filename(filename) if 'IND_' not in filename else 'total')
                    else:
                        weight_args_levels = (econ_model, econ_scenario)
                        
                    if 'aggregate-weighting' in config and config['aggregate-weighting'] == 'agecohorts':
                        weight_args_aggregate = (econ_model, econ_scenario, agecohorts.age_from_filename(filename) if 'IND_' not in filename else 'total')
                        weight_args_aggregate_denom = None
                    else:
                        if 'aggregate-weighting-numerator' in config and config['aggregate-weighting-numerator'] == 'agecohorts':
                            weight_args_aggregate = (econ_model, econ_scenario, agecohorts.age_from_filename(filename) if 'IND_' not in filename else 'total')
                        else:
                            weight_args_aggregate = (econ_model, econ_scenario)
                            
                        if 'aggregate-weighting-denominator' in config and config['aggregate-weighting-denominator'] == 'agecohorts':
                            weight_args_aggregate_denom = (econ_model, econ_scenario, agecohorts.age_from_filename(filename) if 'IND_' not in filename else 'total')
                        else:
                            weight_args_aggregate_denom = (econ_model, econ_scenario)

                # Catch any kind of failure
                try:
                    # Generate levels (e.g., total deaths)
                    if halfweight_levels:
                        outfilename = fullfile(filename, levels_suffix, config)
                        if not missing_only or not checks.check_result_100years(os.path.join(targetdir, outfilename), variable=variable, regioncount=regioncount) or not os.path.exists(os.path.join(targetdir, outfilename)):
                            make_levels(targetdir, filename, outfilename, halfweight_levels, weight_args_levels, config=config)

                    # Aggregate impacts
                    if halfweight_aggregate:
                        outfilename = fullfile(filename, suffix, config)
                        if isinstance(debug_aggregate, str) or not missing_only or not checks.check_result_100years(os.path.join(targetdir, outfilename), variable=variable, regioncount=5665) or not os.path.exists(os.path.join(targetdir, outfilename)):
                            make_aggregates(targetdir, filename, outfilename, halfweight_aggregate, weight_args_aggregate, halfweight_denom=halfweight_aggregate_denom, weight_args_denom=weight_args_aggregate_denom, config=config)

                    if '-noadapt' not in filename and '-incadapt' not in filename and 'histclim' not in filename and 'indiamerge' not in filename:
                        # Generate costs
                        outfilename = fullfile(filename, costs_suffix, config)
                        if not missing_only or not os.path.exists(os.path.join(targetdir, outfilename)) or not checks.check_result_100years(os.path.join(targetdir, outfilename), variable='costs_lb', regioncount=5665):
                            if '-combined' in filename:
                                # Look for age-specific costs
                                agegroups = ['young', 'older', 'oldest']
                                basenames = [filename[:-4].replace('-combined', '-' + agegroup + '-costs') for agegroup in agegroups]
                                hasall = True
                                for basename in basenames:
                                    if not os.path.exists(os.path.join(targetdir, basename + '.nc4')):
                                        print("Missing " + os.path.join(targetdir, basename + '.nc4'))
                                        hasall = False
                                        break

                                if hasall:
                                    # Combine costs across age-groups
                                    print("Has all component costs")
                                    get_stweights = [lambda year0, year1: halfweight_levels.load(1950, 2100, econ_model, econ_scenario, 'age0-4', shareonly=True), lambda year0, year1: halfweight_levels.load(1950, 2100, econ_model, econ_scenario, 'age5-64', shareonly=True), lambda year0, year1: halfweight_levels.load(1950, 2100, econ_model, econ_scenario, 'age65+', shareonly=True)]
                                    agglib.combine_results(targetdir, filename[:-4] + costs_suffix, basenames, get_stweights, "Combined costs across age-groups for " + filename.replace('-combined.nc4', ''))
                            else:
                                # Prepare arguments to adaptation costs system
                                tavgpath = '/shares/gcp/outputs/temps/%s/%s/climtas.nc4' % (clim_scenario, clim_model)
                                impactspath = os.path.join(targetdir, filename)

                                if 'infix' in config:
                                    fullcostsuffix = '-' + str(config['infix']) + costs_suffix
                                else:
                                    continue # Cannot calculate costs

                                # Call the adaptation costs system
                                print(costs_command % (tavgpath, clim_scenario, clim_model, impactspath, fullcostsuffix))
                                os.system(costs_command % (tavgpath, clim_scenario, clim_model, impactspath, fullcostsuffix))

                        # Levels of costs
                        outfilename = fullfile(filename, costs_suffix + levels_suffix, config)
                        if not missing_only or not os.path.exists(os.path.join(targetdir, outfilename)):
                            make_costs_levels(targetdir, fullfile(filename, costs_suffix, config), outfilename, halfweight_levels, weight_args_levels, config=config)

                        # Aggregate costs
                        outfilename = fullfile(filename, costs_suffix + suffix, config)
                        if not missing_only or not os.path.exists(os.path.join(targetdir, outfilename)):
                            make_costs_aggregate(targetdir, fullfile(filename, costs_suffix, config), outfilename, halfweight_aggregate, weight_args_aggregate, halfweight_denom=halfweight_aggregate_denom, weight_args_denom=weight_args_aggregate_denom, config=config)
                    elif 'indiamerge' in filename:
                        # Just aggregate the costs for indiamerge file

                        # Levels of costs
                        outfilename = filename[:-4].replace('combined', 'combined-costs') + levels_suffix + '.nc4'
                        if not missing_only or not os.path.exists(os.path.join(targetdir, outfilename)):
                            make_costs_levels(targetdir, filename[:-4].replace('combined', 'combined-costs') + '.nc4', outfilename, halfweight_levels, weight_args_levels, config=config)

                        # Aggregate costs
                        outfilename = filename[:-4].replace('combined', 'combined-costs') + suffix + '.nc4'
                        if not missing_only or not os.path.exists(os.path.join(targetdir, outfilename)):
                            make_costs_aggregate(targetdir, filename[:-4].replace('combined', 'combined-costs') + '.nc4', outfilename, halfweight_aggregate, weight_args_aggregate, halfweight_denom=halfweight_aggregate_denom, weight_args_denom=weight_args_aggregate_denom, config=config)

                # On exception, report it and continue
                except Exception as ex:
                    print("Failed.")
                    traceback.print_exc()
                    incomplete = True

        # Release the claim on this directory
        statman.release(targetdir, "Incomplete" if incomplete else "Complete")
        # Make sure all produced files are read-writable by the group
        os.system("chmod g+rw --quiet " + os.path.join(targetdir, "*"))
