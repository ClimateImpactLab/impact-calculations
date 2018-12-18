import os, Queue, traceback, time
import numpy as np
from netCDF4 import Dataset
import nc4writer, agglib, checks, csv
from datastore import weights
from impactlab_tools.utils import paralog

costs_suffix = '-costs'
levels_suffix = '-levels'
suffix = "-aggregated"
missing_only = True

costs_command = "Rscript generate/cost_curves.R \"%s\" \"%s\" \"%s\" \"%s\"" # tavgpath rcp gcm impactspath

CLAIM_TIMEOUT = 24*60*60

batchfilter = lambda batch: True #batch == 'median' or 'batch' in batch
targetdirfilter = lambda targetdir: True #'rcp85' in targetdir #'SSP3' in targetdir and 'Env-Growth' in targetdir

# The full population, if we just read it.
# Dictionary of (halfweight, weight_args, minyear, maxyear) => population
cached_weights = {}

def get_cached_weight(halfweight, weight_args, years):
    global cached_weights

    minyear = min(years)
    maxyear = max(years)

    key = (halfweight, weight_args, minyear, maxyear)
    if key in cached_weights:
        return cached_weights[key]

    print "Loading pop..."
    stweight = halfweight.load(minyear, maxyear, *weight_args)
    print "Loaded."

    cached_weights[key] = stweight
    return stweight

def make_aggregates(targetdir, filename, outfilename, halfweight, weight_args, dimensions_template=None, metainfo=None, limityears=None, halfweight_denom=None, weight_args_denom=None):
    # Find all variables that containing the region dimension
    reader = Dataset(os.path.join(targetdir, filename), 'r', format='NETCDF4')
    if dimensions_template is None:
        dimreader = reader
    else:
        dimreader = Dataset(dimensions_template, 'r', format='NETCDF4')

    readeryears = nc4writer.get_years(dimreader, limityears)

    writer = nc4writer.create(targetdir, outfilename)

    regions = dimreader.variables['regions'][:].tolist()
    originals, prefixes, dependencies = agglib.get_aggregated_regions(regions)

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

    years = nc4writer.make_years_variable(writer)
    years[:] = readeryears

    stweight = get_cached_weight(halfweight, weight_args, years)
    if halfweight_denom:
        if halfweight_denom == weights.HALFWEIGHT_SUMTO1:
            stweight_denom = weights.HALFWEIGHT_SUMTO1
        else:
            stweight_denom = get_cached_weight(halfweight_denom, weight_args_denom, years)
    else:
        stweight_denom = None # Just use the same weight

    nc4writer.make_regions_variable(writer, prefixes, 'aggregated')

    original_indices = {regions[ii]: ii for ii in range(len(regions))}

    for key, variable in agglib.iter_timereg_variables(reader):
        dstvalues = np.zeros((len(years), len(prefixes)))
        srcvalues = variable[:, :]
        for ii in range(len(prefixes)):
            numers = np.zeros(srcvalues.shape[0])
            denoms = np.zeros(srcvalues.shape[0])

            if prefixes[ii] == '':
                withinregions = regions
            else:
                withinregions = originals[prefixes[ii]]

            for original in withinregions:
                wws = stweight.get_time(original)
                numers += wws * np.nan_to_num(srcvalues[:, original_indices[original]]) * np.isfinite(srcvalues[:, original_indices[original]])
                if stweight_denom != weights.HALFWEIGHT_SUMTO1:
                    if stweight_denom:
                        weights_denom = stweight_denom.get_time(original)
                        denoms += weights_denom * np.isfinite(srcvalues[:, original_indices[original]])
                    else:
                        denoms += wws * np.isfinite(srcvalues[:, original_indices[original]])

            if stweight_denom == weights.HALFWEIGHT_SUMTO1:
                dstvalues[:, ii] = numers
            else:
                dstvalues[:, ii] = numers / denoms

        agglib.copy_timereg_variable(writer, variable, key, dstvalues, "(aggregated)", unitchange=lambda unit: unit + '/person')

    reader.close()
    if dimensions_template is not None:
        dimreader.close()
    writer.close()

def make_costs_aggregate(targetdir, filename, outfilename, halfweight, weight_args, halfweight_denom=None, weight_args_denom=None):
    # Assume the following IAM and SSP
    econ_model = 'OCED Env-Growth'
    econ_scenario = 'SSP3_v9_130325'
    dimensions_template = "/shares/gcp/outputs/temps/rcp45/CCSM4/climtas.nc4"
    metainfo = dict(description="Upper and lower bounds costs of adaptation calculation.",
                    version="DEADLY-2016-04-22",
                    dependencies="TEMPERATURES, ADAPTATION-ALL-AGES",
                    author="Tamma Carleton")

    make_aggregates(targetdir, filename, outfilename, halfweight, weight_args, dimensions_template=dimensions_template, metainfo=metainfo, halfweight_denom=halfweight_denom, weight_args_denom=weight_args_denom)

def make_levels(targetdir, filename, outfilename, halfweight, weight_args, dimensions_template=None, metainfo=None, limityears=None):
    # Find all variables that containing the region dimension
    reader = Dataset(os.path.join(targetdir, filename), 'r', format='NETCDF4')
    if dimensions_template is None:
        dimreader = reader
    else:
        dimreader = Dataset(dimensions_template, 'r', format='NETCDF4')

    regions = dimreader.variables['regions'][:].tolist()

    writer = nc4writer.create(targetdir, outfilename)

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

    years = nc4writer.make_years_variable(writer)
    years[:] = nc4writer.get_years(dimreader, limityears)
    nc4writer.make_regions_variable(writer, regions, 'regions')

    stweight = get_cached_weight(halfweight, weight_args, years)

    if 'vcv' in reader.variables:
        vcv = reader.variables['vcv'][:, :]
        rootgrp.createDimension('coefficient', vcv.shape[0])
    else:
        vcv = None
        
    for key, variable in agglib.iter_timereg_variables(reader):
        dstvalues = np.zeros((len(years), len(regions)))
        if vcv is None:
            srcvalues = variable[:, :]
            for ii in range(len(regions)):
                dstvalues[:, ii] = srcvalues[:, ii] * stweight.get_time(regions[ii])
        else:
            coeffvalues = np.zeros((vcv.shape[0], len(years), len(regions)))
            srcvalues = reader.variables[key + '_bcde'][:, :, :]
            for ii in range(len(regions)):
                coeffvalues[:, :, ii] = srcvalues[:, :, ii] * stweight.get_time(regions[ii])
                for tt in range(len(years)):
                    dstvalues[tt, ii] = vcv.dot(coeffvalues[:, tt, ii]).dot(coeffvalues[:, tt, ii])

            coeffcolumn = writer.createVariable(key + '_bcde', 'f4', ('coefficient', 'year', 'region'))
            coeffcolumn[:, :, :] = coeffvalues

        agglib.copy_timereg_variable(writer, variable, key, dstvalues, "(levels)", unitchange=lambda unit: unit.replace('/person', ''))

    reader.close()
    if dimensions_template is not None:
        dimreader.close()
    writer.close()

def make_costs_levels(targetdir, filename, outfilename, halfweight, weight_args):
    # Assume the following IAM and SSP
    econ_model = 'OCED Env-Growth'
    econ_scenario = 'SSP3_v9_130325'
    dimensions_template = "/shares/gcp/outputs/temps/rcp45/CCSM4/climtas.nc4"
    metainfo = dict(description="Upper and lower bounds costs of adaptation calculation.",
                    version="DEADLY-2016-04-22",
                    dependencies="TEMPERATURES, ADAPTATION-ALL-AGES",
                    author="Tamma Carleton")

    make_levels(targetdir, filename, outfilename, halfweight, weight_args, dimensions_template=dimensions_template, metainfo=metainfo)

def fullfile(filename, suffix, config):
    if 'infix' in config:
        return fullfile(filename, '-' + config['infix'] + suffix, {})

    return filename[:-4] + suffix + '.nc4'
    
if __name__ == '__main__':
    import sys
    from impactlab_tools.utils import files
    from datastore import population, agecohorts

    config = files.get_allargv_config()

    statman = paralog.StatusManager('aggregate', "generate.aggregate " + sys.argv[1], 'logs', CLAIM_TIMEOUT)

    ## Determine weights
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
            if 'aggregate-weighting-numerator' in config:
                halfweight_aggregate = weights.interpret_halfweight(config['aggregate-weighting-numerator'])
                halfweight_aggregate_denom = weights.interpret_halfweight(config['aggregate-weighting-denominator'])
            else:
                halfweight_aggregate = None
                halfweight_aggregate_denom = None

    for batch, clim_scenario, clim_model, econ_scenario, econ_model, targetdir in agglib.iterresults(config['outputdir'], agglib.make_batchfilter(config), targetdirfilter):
        if not agglib.config_targetdirfilter(clim_scenario, clim_model, econ_scenario, econ_model, targetdir, config):
            continue
        
        print targetdir
        print econ_model, econ_scenario

        if not statman.claim(targetdir) and 'targetdir' not in config:
            continue

        incomplete = False

        for filename in os.listdir(targetdir):
            if filename[-4:] == '.nc4' and suffix not in filename and costs_suffix not in filename and levels_suffix not in filename:
                if 'basename' in config:
                    if config['basename'] not in filename[:-4]:
                        continue
                    
                print filename

                if filename == 'covariates.nc4':
                    variable = 'loggdppc'
                else:
                    variable = 'rebased'

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

                if not checks.check_result_100years(os.path.join(targetdir, filename), variable=variable):
                    print "Incomplete."
                    incomplete = True
                    continue

                try:
                    # Generate total deaths
                    if halfweight_levels:
                        outfilename = fullfile(filename, levels_suffix, config)
                        if not missing_only or not checks.check_result_100years(os.path.join(targetdir, outfilename), variable=variable) or not os.path.exists(os.path.join(targetdir, outfilename)):
                            make_levels(targetdir, filename, outfilename, halfweight_levels, weight_args_levels)

                    # Aggregate impacts
                    if halfweight_aggregate:
                        outfilename = fullfile(filename, suffix, config)
                        if not missing_only or not checks.check_result_100years(os.path.join(targetdir, outfilename), variable=variable, regioncount=5665) or not os.path.exists(os.path.join(targetdir, outfilename)):
                            make_aggregates(targetdir, filename, outfilename, halfweight_aggregate, weight_args_aggregate, halfweight_denom=halfweight_aggregate_denom, weight_args_denom=weight_args_aggregate_denom)

                    if '-noadapt' not in filename and '-incadapt' not in filename and 'histclim' not in filename and 'indiamerge' not in filename:
                        # Generate costs
                        if not missing_only or not os.path.exists(os.path.join(targetdir, fullfile(filename, costs_suffix, config))):
                            if '-combined' in filename:
                                # Look for age-specific costs
                                agegroups = ['young', 'older', 'oldest']
                                basenames = [filename[:-4].replace('-combined', '-' + agegroup + '-costs') for agegroup in agegroups]
                                hasall = True
                                for basename in basenames:
                                    if not os.path.exists(os.path.join(targetdir, basename + '.nc4')):
                                        print "Missing " + os.path.join(targetdir, basename + '.nc4')
                                        hasall = False
                                        break

                                if hasall:
                                    print "Has all component costs"
                                    get_stweights = [lambda year0, year1: halfweight_levels.load(1981, 2100, econ_model, econ_scenario, 'age0-4'), lambda year0, year1: halfweight_levels.load(1981, 2100, econ_model, econ_scenario, 'age5-64'), lambda year0, year1: halfweight_levels.load(1981, 2100, econ_model, econ_scenario, 'age65+')]
                                    agglib.combine_results(targetdir, filename[:-4] + costs_suffix, basenames, get_stweights, "Combined costs across age-groups for " + filename.replace('-combined.nc4', ''))
                            else:
                                tavgpath = '/shares/gcp/outputs/temps/%s/%s/climtas.nc4' % (clim_scenario, clim_model)
                                impactspath = os.path.join(targetdir, filename)
                                gammapath = '/shares/gcp/social/parameters/mortality/Diagnostics_Apr17/' + filename.replace('.nc4', '.csvv')
                                gammapath = gammapath.replace('-young', '').replace('-older', '').replace('-oldest', '')

                                if 'POLY-4' in filename:
                                    numpreds = 4
                                    minpath = os.path.join(targetdir, filename.replace('.nc4', '-polymins.csv'))
                                elif 'POLY-5' in filename:
                                    numpreds = 5
                                    minpath = os.path.join(targetdir, filename.replace('.nc4', '-polymins.csv'))
                                elif 'CSpline' in filename:
                                    numpreds = 5
                                    minpath = os.path.join(targetdir, filename.replace('.nc4', '-splinemins.csv'))
                                else:
                                    ValueError('Unknown functional form')
                                
                                if '-young' in filename:
                                    gammarange = '1:%s' % (numpreds * 3)
                                elif '-older' in filename:
                                    gammarange = '%s:%s' % (numpreds * 3 + 1, numpreds * 6)
                                elif '-oldest' in filename:
                                    gammarange = '%s:%s' % (numpreds * 6 + 1, numpreds * 9)
                                else:
                                    continue # Cannot calculate costs
                                
                                print costs_command % (tavgpath, clim_scenario, clim_model, impactspath)
                                os.system(costs_command % (tavgpath, clim_scenario, clim_model, impactspath))

                        # Levels of costs
                        outfilename = fullfile(filename, costs_suffix + levels_suffix, config)
                        if not missing_only or not os.path.exists(os.path.join(targetdir, outfilename)):
                            make_costs_levels(targetdir, fullfile(filename, costs_suffix, config), outfilename, halfweight_levels, weight_args_levels)

                        # Aggregate costs
                        outfilename = fullfile(filename, costs_suffix + suffix, config)
                        if not missing_only or not os.path.exists(os.path.join(targetdir, outfilename)):
                            make_costs_aggregate(targetdir, fullfile(filename, costs_suffix, config), outfilename, halfweight_aggregate, weight_args_aggregate, halfweight_denom=halfweight_aggregate_denom, weight_args_denom=weight_args_aggregate_denom)
                    elif 'indiamerge' in filename:
                        # Just aggregate the costs

                        # Levels of costs
                        outfilename = filename[:-4].replace('combined', 'combined-costs') + levels_suffix + '.nc4'
                        if not missing_only or not os.path.exists(os.path.join(targetdir, outfilename)):
                            make_costs_levels(targetdir, filename[:-4].replace('combined', 'combined-costs') + '.nc4', outfilename, halfweight_levels, weight_args_levels)

                        # Aggregate costs
                        outfilename = filename[:-4].replace('combined', 'combined-costs') + suffix + '.nc4'
                        if not missing_only or not os.path.exists(os.path.join(targetdir, outfilename)):
                            make_costs_aggregate(targetdir, filename[:-4].replace('combined', 'combined-costs') + '.nc4', outfilename, halfweight_aggregate, weight_args_aggregate, halfweight_denom=halfweight_aggregate_denom, weight_args_denom=weight_args_aggregate_denom)
                        
                except Exception as ex:
                    print "Failed."
                    traceback.print_exc()
                    incomplete = True

        statman.release(targetdir, "Incomplete" if incomplete else "Complete")
        os.system("chmod g+rw " + os.path.join(targetdir, "*"))
