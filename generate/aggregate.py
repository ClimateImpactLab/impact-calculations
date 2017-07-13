import os, Queue, traceback, time
import numpy as np
from netCDF4 import Dataset
import nc4writer, agglib, checks, csv
from impactlab_tools.utils import paralog

costs_suffix = '-costs'
levels_suffix = '-levels'
suffix = "-aggregated"
missing_only = True

costs_command = "Rscript generate/cost_curves.R \"%s\" \"%s\" \"%s\" \"%s\"" # tavgpath rcp gcm impactspath

CLAIM_TIMEOUT = 60*60

batchfilter = lambda batch: batch == 'median' or 'batch' in batch
targetdirfilter = lambda targetdir: 'rcp85' in targetdir #'SSP3' in targetdir and 'Env-Growth' in targetdir

# The full population, if we just read it.  Only 1 at a time (it's big!)
# Tuple of (get_population, minyear, maxyear, population)
cached_population = None

def get_cached_population(get_population, years):
    global cached_population

    minyear = min(years)
    maxyear = max(years)

    if cached_population is not None:
        if cached_population[0] == get_population and cached_population[1] == minyear and cached_population[2] == maxyear:
            return cached_population[3]

    print "Loading pop..."
    stweight = get_population(minyear, maxyear)
    print "Loaded."

    cached_population = (get_population, minyear, maxyear, stweight)
    return stweight

def make_aggregates(targetdir, filename, get_population, dimensions_template=None, metainfo=None, limityears=None):
    # Find all variables that containing the region dimension
    reader = Dataset(os.path.join(targetdir, filename), 'r', format='NETCDF4')
    if dimensions_template is None:
        dimreader = reader
    else:
        dimreader = Dataset(dimensions_template, 'r', format='NETCDF4')

    readeryears = nc4writer.get_years(dimreader, limityears)

    writer = nc4writer.create(targetdir, filename[:-4] + suffix)

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

    stweight = get_cached_population(get_population, years)

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
                weights = stweight.get_time(original)
                numers += weights * np.nan_to_num(srcvalues[:, original_indices[original]]) * np.isfinite(srcvalues[:, original_indices[original]])
                denoms += weights * np.isfinite(srcvalues[:, original_indices[original]])

            dstvalues[:, ii] = numers / denoms

        agglib.copy_timereg_variable(writer, variable, key, dstvalues, "(aggregated)", unitchange=lambda unit: unit + '/person')

    reader.close()
    if dimensions_template is not None:
        dimreader.close()
    writer.close()

def make_costs_aggregate(targetdir, filename, get_population):
    # Assume the following IAM and SSP
    econ_model = 'OCED Env-Growth'
    econ_scenario = 'SSP3_v9_130325'
    dimensions_template = "/shares/gcp/outputs/temps/rcp45/CCSM4/climtas.nc4"
    metainfo = dict(description="Upper and lower bounds costs of adaptation calculation.",
                    version="DEADLY-2016-04-22",
                    dependencies="TEMPERATURES, ADAPTATION-ALL-AGES",
                    author="Tamma Carleton")

    make_aggregates(targetdir, filename, get_population, dimensions_template=dimensions_template, metainfo=metainfo)

def make_levels(targetdir, filename, get_population, dimensions_template=None, metainfo=None, limityears=None):
    # Find all variables that containing the region dimension
    reader = Dataset(os.path.join(targetdir, filename), 'r', format='NETCDF4')
    if dimensions_template is None:
        dimreader = reader
    else:
        dimreader = Dataset(dimensions_template, 'r', format='NETCDF4')

    regions = dimreader.variables['regions'][:].tolist()

    writer = nc4writer.create(targetdir,  filename[:-4] + levels_suffix)

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

    stweight = get_cached_population(get_population, years)

    for key, variable in agglib.iter_timereg_variables(reader):
        dstvalues = np.zeros((len(years), len(regions)))
        srcvalues = variable[:, :]
        for ii in range(len(regions)):
            dstvalues[:, ii] = srcvalues[:, ii] * stweight.get_time(regions[ii])

        agglib.copy_timereg_variable(writer, variable, key, dstvalues, "(levels)", unitchange=lambda unit: unit.replace('/person', ''))

    reader.close()
    if dimensions_template is not None:
        dimreader.close()
    writer.close()

def make_costs_levels(targetdir, filename, get_population):
    # Assume the following IAM and SSP
    econ_model = 'OCED Env-Growth'
    econ_scenario = 'SSP3_v9_130325'
    dimensions_template = "/shares/gcp/outputs/temps/rcp45/CCSM4/climtas.nc4"
    metainfo = dict(description="Upper and lower bounds costs of adaptation calculation.",
                    version="DEADLY-2016-04-22",
                    dependencies="TEMPERATURES, ADAPTATION-ALL-AGES",
                    author="Tamma Carleton")

    make_levels(targetdir, filename, get_population, dimensions_template=dimensions_template, metainfo=metainfo)

if __name__ == '__main__':
    import sys
    from impactlab_tools.utils import files
    from datastore import population, agecohorts

    config = files.get_argv_config()

    statman = paralog.StatusManager('aggregate', "generate.aggregate " + sys.argv[1], 'logs', CLAIM_TIMEOUT)
    
    if config['weighting'] == 'agecohorts':
        halfweight = agecohorts.SpaceTimeBipartiteData(1981, 2100, None)
    else:
        halfweight = population.SpaceTimeBipartiteData(1981, 2100, None)

    for batch, clim_scenario, clim_model, econ_scenario, econ_model, targetdir in agglib.iterresults(config['outputdir']):
        print targetdir
        print econ_model, econ_scenario

        if not statman.claim(targetdir):
            continue

        incomplete = False

        for filename in os.listdir(targetdir):
            if filename[-4:] == '.nc4' and suffix not in filename and costs_suffix not in filename and levels_suffix not in filename:
                print filename

                if filename == 'covariates.nc4':
                    variable = 'loggdppc'
                else:
                    variable = 'rebased'

                if config['weighting'] == 'agecohorts':
                    get_population = lambda year0, year1: halfweight.load_population(year0, year1, econ_model, econ_scenario, agecohorts.age_from_filename(filename) if 'IND_' not in filename else 'total')
                else:
                    get_population = lambda year0, year1: halfweight.load_population(year0, year1, econ_model, econ_scenario)

                if not checks.check_result_100years(os.path.join(targetdir, filename), variable=variable):
                    print "Incomplete."
                    incomplete = True
                    continue

                try:
                    # Generate total deaths
                    if not missing_only or not checks.check_result_100years(os.path.join(targetdir, filename[:-4] + levels_suffix + '.nc4'), variable=variable) or not os.path.exists(os.path.join(targetdir, filename[:-4] + levels_suffix + '.nc4')):
                        make_levels(targetdir, filename, get_population)

                    # Aggregate impacts
                    if not missing_only or not checks.check_result_100years(os.path.join(targetdir, filename[:-4] + suffix + '.nc4'), variable=variable, regioncount=5665) or not os.path.exists(os.path.join(targetdir, filename[:-4] + suffix + '.nc4')):
                        make_aggregates(targetdir, filename, get_population)

                    if '-noadapt' not in filename and '-incadapt' not in filename and 'histclim' not in filename:
                        # Generate costs
                        if not missing_only or not os.path.exists(os.path.join(targetdir, filename[:-4] + costs_suffix + '.nc4')):
                            if '-combined' in filename:
                                # Look for age-specific costs
                                agegroups = ['young', 'older', 'oldest']
                                basenames = [filename[:-4].replace('-combined', '-' + agegroup + '-costs') for agegroup in agegroups]
                                hasall = True
                                for basename in basenames:
                                    if not os.path.exists(os.path.join(targetdir, basename + '.nc4')):
                                        hasall = False
                                        break

                                if hasall:
                                    get_stweights = [lambda year0, year1: halfweight.load_population(1981, 2100, econ_model, econ_scenario, 'age0-4'), lambda year0, year1: halfweight.load_population(1981, 2100, econ_model, econ_scenario, 'age5-64'), lambda year0, year1: halfweight.load_population(1981, 2100, econ_model, econ_scenario, 'age65+')]
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
                        if not missing_only or not os.path.exists(os.path.join(targetdir, filename[:-4] + costs_suffix + levels_suffix + '.nc4')):
                            make_costs_levels(targetdir, filename[:-4] + costs_suffix + '.nc4', get_population)

                        # Aggregate costs
                        if not missing_only or not os.path.exists(os.path.join(targetdir, filename[:-4] + costs_suffix + suffix + '.nc4')):
                            make_costs_aggregate(targetdir, filename[:-4] + costs_suffix + '.nc4', get_population)

                except Exception as ex:
                    print "Failed."
                    traceback.print_exc()
                    incomplete = True

        statman.release(targetdir, "Incomplete" if incomplete else "Complete")
