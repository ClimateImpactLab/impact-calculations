"""Climate covariates generation tool.

This tool creates files stored in the /shares/gcp/outputs/temps
directory, which describe climate variables at the annual level and
averaged covariates.

Sets of files are defined by their filename and the filename to be
generated is set at the top (under Options).

This is then used to select a climate data discoverer, a list of
names, and a corresponding list of functions that extract the relevant
data from the climate data xarray object.
"""

import sys, os
import numpy as np
from netCDF4 import Dataset
import weather, nc4writer
from climate import discover
from impactlab_tools.utils import files
from impactcommon.math import averages

# Options
filename = 'dd_tasmax.nc4'
only_missing = True

outputdir = '/shares/gcp/outputs/temps'

standard_running_mean_init = averages.BartlettAverager
numtempyears = 30

# Determine the basic objects to construct the result
if filename == 'climtas.nc4':
    discoverer = discover.discover_versioned(files.sharedpath('climate/BCSD/hierid/popwt/daily/tas'), 'tas')
    covar_names = ['climtas']
    annual_calcs = [lambda ds: np.mean(ds['tas'])] # Average within each year

if filename == 'dd_tasmax.nc4':
    discoverer = discover.discover_yearly_variables(files.sharedpath('climate/BCSD/aggregation/cmip5_new/IR_level'),
                                                    'Degreedays_tasmax', 'coldd_agg', 'hotdd_agg')
    covar_names = ['climcold-tasmax', 'climhot-tasmax']
    annual_calcs = [lambda ds: ds.coldd_agg, lambda ds: ds.hotdd_agg]

# Iterate through weather datasets
for clim_scenario, clim_model, weatherbundle in weather.iterate_bundles(discoverer):
    print clim_scenario, clim_model
    targetdir = os.path.join(outputdir, clim_scenario, clim_model)

    # Check if we should generate a file for this targetdir
    if only_missing and os.path.exists(os.path.join(targetdir, filename)):
        continue
        
    print targetdir
    if not os.path.exists(targetdir):
        os.makedirs(targetdir, 0775)

    # Construct the NetCDF file
    rootgrp = Dataset(os.path.join(targetdir, filename), 'w', format='NETCDF4')
    rootgrp.description = "Yearly and 30-year Bartlett average temperatures."
    rootgrp.author = "James Rising"

    years = nc4writer.make_years_variable(rootgrp)
    regions = nc4writer.make_regions_variable(rootgrp, weatherbundle.regions, None)

    covar = rootgrp.createDimension('covar', len(covar_names))
    covars = rootgrp.createVariable('covars', str, ('covar',))
    covars.long_title = "Covariate name"

    for kk in range(len(covar_names)):
        covars[kk] = covar_names[kk]

    yeardata = weatherbundle.get_years()
    years[:] = yeardata

    # Create the main output variables
    annual = rootgrp.createVariable("annual", 'f4', ('year', 'region', 'covar'))
    averaged = rootgrp.createVariable("averaged", 'f4', ('year', 'region', 'covar'))

    annualdata = np.zeros((len(yeardata), len(weatherbundle.regions), len(covar_names)))
    averageddata = np.zeros((len(yeardata), len(weatherbundle.regions), len(covar_names)))

    # Start up all the running means
    regiondata = []
    for ii in range(len(weatherbundle.regions)):
        covardata = []
        for jj in range(len(covar_names)):
            covardata.append(standard_running_mean_init([], numtempyears))
        regiondata.append(covardata)

    # Handle data for each year and region
    print "Processing years..."
    yy = 0
    for year, ds in weatherbundle.yearbundles():
        print "Push", year

        for ii in range(len(weatherbundle.regions)):
            # Extract each weather variable
            for kk in range(len(covar_names)):
                yearval = annual_calcs[kk](ds.isel(region=ii))
                annualdata[yy, ii, kk] = yearval
                regiondata[ii][kk].update(yearval)
                averageddata[yy, ii, kk] = regiondata[ii][kk].get()
        yy += 1

    # Finalize the NetCDF file
    annual[:, :, :] = annualdata
    averaged[:, :, :] = averageddata

    rootgrp.close()

