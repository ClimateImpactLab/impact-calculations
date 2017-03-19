import sys, os
import numpy as np
from netCDF4 import Dataset
import weather, nc4writer
from adaptation.covariates import rm_init, rm_add, rm_mean
from climate.discover import discover_variable

discoverer = discover_variable('/shares/gcp/climate/BCSD/aggregation/cmip5/IR_level', 'tas')
outputdir = '/shares/gcp/output/temps'
filename = 'climtas.nc4'

covar_names = ['climtas']
covar_calcs = [lambda temps: np.mean(temps)]

numtempyears = 15

for clim_scenario, clim_model, weatherbundle in weather.iterate_bundles(discoverer):
    print clim_scenario, clim_model
    targetdir = os.path.join(outputdir, clim_scenario, clim_model)

    print targetdir
    if not os.path.exists(targetdir):
        os.makedirs(targetdir)

    rootgrp = Dataset(os.path.join(targetdir, filename), 'w', format='NETCDF4')
    rootgrp.description = "Yearly and 15-year average temperatures."
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

    annual = rootgrp.createVariable("annual", 'f8', ('year', 'region', 'covar'))
    averaged = rootgrp.createVariable("averaged", 'f8', ('year', 'region', 'covar'))

    annualdata = np.zeros((len(yeardata), len(weatherbundle.regions), len(covar_names)))
    averageddata = np.zeros((len(yeardata), len(weatherbundle.regions), len(covar_names)))

    # Start up all the rms
    regiondata = []
    for ii in range(len(weatherbundle.regions)):
        covardata = []
        for jj in range(len(covar_names)):
            covardata.append(rm_init([]))
        regiondata.append(covardata)

    print "Processing years..."
    yy = 0
    for yyyyddd, temps in weatherbundle.yearbundles():
        print "Push", int(yyyyddd[0] / 1000)

        for ii in range(len(weatherbundle.regions)):
            for kk in range(len(covar_names)):
                yearval = covar_calcs[kk](temps[:, ii])
                annualdata[yy, ii, kk] = yearval
                rm_add(regiondata[ii][kk], yearval, numtempyears)
                averageddata[yy, ii, kk] = rm_mean(regiondata[ii][kk])
        yy += 1

    annual[:, :, :] = annualdata
    averaged[:, :, :] = averageddata

    rootgrp.close()

