import os, Queue, traceback
import numpy as np
from netCDF4 import Dataset
import nc4writer, agglib, checks

costs_suffix = '-costs'
levels_suffix = '-levels'
suffix = "-aggregated"
missing_only = True

costs_command = "Rscript generate/cost_curves.R \"%s\" %s" # resultfile tempsfile

checkfile = 'check-20161230.txt'

batchfilter = lambda batch: batch == 'median' or 'batch' in batch
targetdirfilter = lambda targetdir: True #'SSP3' in targetdir and 'Env-Growth' in targetdir and checkfile not in os.listdir(targetdir)

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

def iterdir(basedir):
    for filename in os.listdir(basedir):
        yield filename, os.path.join(os.path.join(basedir, filename))

def iterresults(outdir):
    for batch, batchpath in iterdir(outdir):
        if not batchfilter(batch):
            continue
        for clim_scenario, cspath in iterdir(batchpath):
            for clim_model, cmpath in iterdir(cspath):
                for econ_model, empath in iterdir(cmpath):
                    for econ_scenario, espath in iterdir(empath):
                        if not targetdirfilter(espath):
                            continue
                        yield batch, clim_scenario, clim_model, econ_scenario, econ_model, espath

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

def make_aggregates(targetdir, filename, get_population, dimensions_template=None, metainfo=None, limityears=None):
    # Find all variables that containing the region dimension
    reader = Dataset(os.path.join(targetdir, filename), 'r', format='NETCDF4')
    if dimensions_template is None:
        dimreader = reader
    else:
        dimreader = Dataset(dimensions_template, 'r', format='NETCDF4')

    readeryears = get_years(dimreader, limityears)

    if os.path.exists(os.path.join(targetdir, filename[:-4] + suffix + '.nc4')):
        os.remove(os.path.join(targetdir, filename[:-4] + suffix + '.nc4')) # Needs to be deleted
    writer = Dataset(os.path.join(targetdir, filename[:-4] + suffix + '.nc4'), 'w', format='NETCDF4')

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
                numers += weights * srcvalues[:, original_indices[original]]
                denoms += weights

            dstvalues[:, ii] = numers / denoms

        agglib.copy_timereg_variable(writer, variable, key, dstvalues, "(aggregated)")

    reader.close()
    if dimensions_template is not None:
        dimreader.close()
    writer.close()

def make_costs_aggregate(targetdir, filename, get_population):
    # Assume the following IAM and SSP
    econ_model = 'OCED Env-Growth'
    econ_scenario = 'SSP3_v9_130325'
    dimensions_template = "/shares/gcp/outputs/temps/rcp45/CCSM4/temps.nc4"
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

    if os.path.exists(os.path.join(targetdir, filename[:-4] + levels_suffix + '.nc4')):
        os.remove(os.path.join(targetdir, filename[:-4] + levels_suffix + '.nc4')) # Needs to be deleted
    writer = Dataset(os.path.join(targetdir, filename[:-4] + levels_suffix + '.nc4'), 'w', format='NETCDF4')

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
    years[:] = get_years(dimreader, limityears)
    nc4writer.make_regions_variable(writer, regions, 'regions')

    stweight = get_cached_population(get_population, years)

    for key, variable in agglib.iter_timereg_variables(reader):
        dstvalues = np.zeros((len(years), len(regions)))
        srcvalues = variable[:, :]
        for ii in range(len(regions)):
            dstvalues[:, ii] = srcvalues[:, ii] * stweight.get_time(regions[ii])

        agglib.copy_timereg_variable(writer, variable, key, dstvalues, "(levels)")

    reader.close()
    if dimensions_template is not None:
        dimreader.close()
    writer.close()

def make_costs_levels(targetdir, filename, get_population):
    # Assume the following IAM and SSP
    econ_model = 'OCED Env-Growth'
    econ_scenario = 'SSP3_v9_130325'
    dimensions_template = "/shares/gcp/outputs/temps/rcp45/CCSM4/temps.nc4"
    metainfo = dict(description="Upper and lower bounds costs of adaptation calculation.",
                    version="DEADLY-2016-04-22",
                    dependencies="TEMPERATURES, ADAPTATION-ALL-AGES",
                    author="Tamma Carleton")

    make_levels(targetdir, filename, get_population, dimensions_template=dimensions_template, metainfo=metainfo)

if __name__ == '__main__':
    import sys
    from datastore import population
    outputdir = sys.argv[1]

    halfweight = population.SpaceTimeBipartiteData(1981, 2100, None)

    for batch, clim_scenario, clim_model, econ_scenario, econ_model, targetdir in iterresults(outputdir):
        print targetdir
        print econ_model, econ_scenario

        with open(os.path.join(targetdir, checkfile), 'w') as fp:
            fp.write("START")

        incomplete = False
        get_population = lambda year0, year1: halfweight.load_population(year0, year1, econ_model, econ_scenario)

        for filename in os.listdir(targetdir):
            if filename[-4:] == '.nc4' and suffix not in filename and costs_suffix not in filename and levels_suffix not in filename:
                print filename

                if filename == 'covariates.nc4':
                    variable = 'tas'
                else:
                    variable = 'rebased'

                if not checks.check_result_100years(os.path.join(targetdir, filename), variable=variable):
                    print "Incomplete."
                    incomplete = True
                    continue

                try:
                    if filename in ['interpolated_mortality_all_ages.nc4', 'interpolated_mortality65_plus.nc4', 'global_interaction_best.nc4', 'global_interaction_gmfd.nc4', 'global_interaction_no_popshare_best.nc4', 'global_interaction_no_popshare_gmfd.nc4', 'moratlity_cubic_splines_2factors_gmfd_031617.nc4', 'moratlity_cubic_splines_2factors_best_031617.nc4']:
                        # Generate costs
                        # tempsfile = '/shares/gcp/outputs/temps/%s/%s/temps.nc4' % (clim_scenario, clim_model)

                        # if not missing_only or not os.path.exists(os.path.join(targetdir, filename[:-4] + costs_suffix + '.nc4')):
                        #     os.system(costs_command % (os.path.join(targetdir, filename), tempsfile))

                        # Levels of costs
                        if not missing_only or not os.path.exists(os.path.join(targetdir, filename[:-4] + costs_suffix + levels_suffix + '.nc4')):
                            make_costs_levels(targetdir, filename[:-4] + costs_suffix + '.nc4', get_population)

                        # Aggregate costs
                        if not missing_only or not os.path.exists(os.path.join(targetdir, filename[:-4] + costs_suffix + suffix + '.nc4')):
                            make_costs_aggregate(targetdir, filename[:-4] + costs_suffix + '.nc4', get_population)

                    # Generate total deaths
                    if not missing_only or not checks.check_result_100years(os.path.join(targetdir, filename[:-4] + levels_suffix + '.nc4'), variable=variable) or not os.path.exists(os.path.join(targetdir, filename[:-4] + levels_suffix + '.nc4')):
                        make_levels(targetdir, filename, get_population)

                    # Aggregate impacts
                    if not missing_only or not checks.check_result_100years(os.path.join(targetdir, filename[:-4] + suffix + '.nc4'), variable=variable, regioncount=5665) or not os.path.exists(os.path.join(targetdir, filename[:-4] + suffix + '.nc4')):
                        make_aggregates(targetdir, filename, get_population)

                except Exception as ex:
                    print "Failed."
                    traceback.print_exc()
                    incomplete = True

        if incomplete:
            os.remove(os.path.join(targetdir, checkfile))
        else:
            with open(os.path.join(targetdir, checkfile), 'w') as fp:
                fp.write("END")

