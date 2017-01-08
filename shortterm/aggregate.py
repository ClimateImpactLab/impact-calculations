import os, Queue
import numpy as np
from netCDF4 import Dataset
from generate import nc4writer, agglib

suffix = "-aggregated"
checkfile = 'check-20161227.txt'

def iterdir(basedir):
    # Do median first
    if 'median' in os.listdir(basedir):
        yield 'median', os.path.join(os.path.join(basedir, 'median'))
    for filename in os.listdir(basedir):
        if filename != 'median':
            yield filename, os.path.join(os.path.join(basedir, filename))

def iterresults(outdir):
    for batch1, batch1path in iterdir(outdir):
        for batch2, batch12path in iterdir(batch1path):
            yield batch12path

def make_aggregates(targetdir, filename, stweight):
    # Find all variables that containing the region dimension
    reader = Dataset(os.path.join(targetdir, filename), 'r', format='NETCDF4')
    readermonths = reader.variables['month'][:]

    writer = Dataset(os.path.join(targetdir, filename[:-4] + suffix + '.nc4'), 'w', format='NETCDF4')

    regions = reader.variables['regions'][:].tolist()
    originals, prefixes, dependencies = agglib.get_aggregated_regions(regions)

    writer.description = reader.description + " (aggregated)"
    writer.version = reader.version
    writer.dependencies = ', '.join(dependencies) + ', ' + reader.version
    writer.author = reader.author

    months = nc4writer.make_months_variable(writer, 'Months since 1960-01-01')
    months[:] = readermonths

    month2years1981 = []
    for month in months:
        month2years1981 = int(month / 12) - 21 # month values to year values, with 0 = 1981

    nc4writer.make_regions_variable(writer, prefixes, 'aggregated')

    original_indices = {regions[ii]: ii for ii in range(len(regions))}

    for key, variable in agglib.iter_timereg_variables(reader, timevar='month'):
        dstvalues = np.zeros((len(months), len(prefixes)))
        srcvalues = variable[:, :]
        for ii in range(len(prefixes)):
            numers = np.zeros(srcvalues.shape[0])
            denoms = np.zeros(srcvalues.shape[0])

            if prefixes[ii] == '':
                withinregions = regions
            else:
                withinregions = originals[prefixes[ii]]

            for original in withinregions:
                weights = stweight.get_time(original)[month2years1981]
                numers += weights * srcvalues[:, original_indices[original]]
                denoms += weights

            dstvalues[:, ii] = numers / denoms

        agglib.copy_timereg_variable(writer, variable, key, dstvalues, "(aggregated)", timevar='month')

    reader.close()
    writer.close()

if __name__ == '__main__':
    import sys
    from datastore import population
    outputdir = sys.argv[1]

    halfweight = population.SpaceTimeBipartiteData(1981, 2020, None)
    stweight = halfweight.load_population(1981, 2020, 'OECD Env-Growth', 'SSP2_v9_130325')

    for targetdir in iterresults(outputdir):
        print targetdir

        if os.path.exists(os.path.join(targetdir, checkfile)):
            continue

        with open(os.path.join(targetdir, checkfile), 'w') as fp:
            fp.write("START")

        for filename in os.listdir(targetdir):
            if filename[-4:] == '.nc4' and suffix not in filename:
                print filename

                # Aggregate impacts
                make_aggregates(targetdir, filename, stweight)

        with open(os.path.join(targetdir, checkfile), 'w') as fp:
            fp.write("END")

