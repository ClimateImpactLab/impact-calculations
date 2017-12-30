import os
import numpy as np
from netCDF4 import Dataset
import nc4writer, agglib

suffix = "-aggregated"
outputdir = '/shares/gcp/outputs/temps'

def iterdir(basedir):
    for filename in os.listdir(basedir):
        yield filename, os.path.join(os.path.join(basedir, filename))

def iterresults(outdir):
    for rcp, batch1path in iterdir(outdir):
        for gcm, batch12path in iterdir(batch1path):
            yield rcp, gcm, batch12path

def make_aggregates(targetdir, filename, stweight):
    # Find all variables that containing the region dimension
    reader = Dataset(os.path.join(targetdir, filename), 'r', format='NETCDF4')
    readeryears = nc4writer.get_years(reader)

    writer = Dataset(os.path.join(targetdir, filename[:-4] + suffix + '.nc4'), 'w', format='NETCDF4')

    regions = reader.variables['regions'][:].tolist()
    originals, prefixes, dependencies = agglib.get_aggregated_regions(regions)

    writer.description = reader.description + " (aggregated)"
    writer.version = "Temps.20171228" #reader.version
    writer.dependencies = ', '.join(dependencies) + ', ' + "Temps.20171228" #reader.version
    writer.author = reader.author

    years = nc4writer.make_years_variable(writer)
    years[:] = readeryears

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

        agglib.copy_timereg_variable(writer, variable, key, dstvalues, "(aggregated)")

    reader.close()
    writer.close()

if __name__ == '__main__':
    import sys
    from datastore import population

    halfweight = population.SpaceTimeBipartiteData(1981, 2099, None)
    stweight = halfweight.load(1981, 2099, 'high', 'SSP2')

    for rcp, gcm, targetdir in iterresults(outputdir):
        print targetdir

        for filename in os.listdir(targetdir):
            if filename[-4:] == '.nc4' and suffix not in filename:
                print filename

                # Aggregate impacts
                make_aggregates(targetdir, filename, stweight)
                
