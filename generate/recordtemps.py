import sys, os
import numpy as np
from netCDF4 import Dataset
import weather, nc4writer
from adaptation.adapting_curve import rm_init, rm_add, rm_mean

basedir = '/shares/gcp/BCSD/grid2reg/cmip5'
outputdir = sys.argv[1]

binlimits = [-np.inf, -17, -12, -7, -2, 3, 8, 13, 18, 23, 28, 33, np.inf]
dropbin = 8
numtempyears = 15

for clim_scenario, clim_model, weatherbundle in weather.iterate_bundles(basedir):
    print clim_scenario, clim_model
    targetdir = os.path.join(outputdir, 'temps', clim_scenario, clim_model)

    print targetdir
    if not os.path.exists(targetdir):
        os.makedirs(targetdir)

    rootgrp = Dataset(os.path.join(targetdir, 'temps.nc4'), 'w', format='NETCDF4')
    rootgrp.description = "Yearly and 15-year average temperatures."
    rootgrp.author = "James Rising"

    years = nc4writer.make_years_variable(rootgrp)
    regions = nc4writer.make_regions_variable(rootgrp, weatherbundle.regions, None)

    tbin = rootgrp.createDimension('tbin', len(binlimits) - 2)

    binlos = rootgrp.createVariable('binlos','i4',('tbin',))
    binlos[:] = [-100] + binlimits[1:dropbin] + binlimits[dropbin+1:-1]

    binhis = rootgrp.createVariable('binhis','i4',('tbin',))
    binhis[:] = binlimits[1:dropbin] + binlimits[dropbin+1:-1] + [100]

    yeardata = weatherbundle.get_years()
    years[:] = yeardata

    annual = rootgrp.createVariable("annual", 'f8', ('year', 'region', 'tbin'))
    averaged = rootgrp.createVariable("averaged", 'f8', ('year', 'region', 'tbin'))

    annualdata = np.zeros((len(yeardata), len(weatherbundle.regions), len(binlimits) - 2))
    averageddata = np.zeros((len(yeardata), len(weatherbundle.regions), len(binlimits) - 2))

    # Start up all the rms
    regiondata = []
    for ii in range(len(weatherbundle.regions)):
        bindata = []
        for jj in range(len(binlimits) - 2):
            bindata.append(rm_init([]))
        regiondata.append(bindata)

    print "Processing years..."
    yy = 0
    for yyyyddd, temps in weatherbundle.yearbundles():
        print "Push", int(yyyyddd[0] / 1000)

        for ii in range(len(weatherbundle.regions)):
            dj = 0
            belowprev = 0
            for jj in range(len(binlimits) - 2):
                belowupper = float(np.sum(temps[:, ii] < binlimits[jj+1]))
                if jj == dropbin:
                    belowprev = belowupper
                    dj = -1
                    continue

                bindays = belowupper - belowprev
                annualdata[yy, ii, jj+dj] = bindays
                rm_add(regiondata[ii][jj+dj], bindays, numtempyears)
                averageddata[yy, ii, jj+dj] = rm_mean(regiondata[ii][jj+dj])
                belowprev = belowupper
            annualdata[yy, ii, -1] = temps.shape[0] - belowprev
            rm_add(regiondata[ii][-1], temps.shape[0] - belowprev, numtempyears)
            averageddata[yy, ii, -1] = rm_mean(regiondata[ii][-1])
        yy += 1

    annual[:, :, :] = annualdata
    averaged[:, :, :] = averageddata

    rootgrp.close()

