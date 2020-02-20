import sys, os
import numpy as np
from netCDF4 import Dataset
import weather, nc4writer
from climate import discover
from openest.generate import fast_dataset
from impactlab_tools.utils import files
from impactcommon.math import averages
from datastore import irvalues
import datetime
from dateutil.relativedelta import relativedelta

filename = 'maize_seasonal_tasmax_test.nc4'
only_missing = False
non_leap_year = 2010

if filename == 'maize_seasonal_tasmax.nc4':
    discoverer = discover.discover_versioned(files.sharedpath('climate/BCSD/hierid/popwt/daily/tasmax'), 'tasmax')
    covar_names = ['seasonal_tasmax']
    seasons = 'daily'
    clim_var = 'tasmax'
    seasonal_filepath = "social/baselines/agriculture/world-combo-201710-growing-seasons-corn-1stseason.csv"

if filename == 'maize_seasonal_pr.nc4':
    discoverer = discover.discover_versioned(files.sharedpath('climate/BCSD/hierid/cropwt/monthly/pr'), 'pr')
    covar_names = ['seasonal_pr']
    seasons = 'daily'
    clim_var = 'pr'
    seasonal_filepath = "social/baselines/agriculture/world-combo-201710-growing-seasons-corn-1stseason.csv"

    
outputdir = '/shares/gcp/outputs/temps'
culture_periods = irvalues.get_file_cached(seasonal_filepath, irvalues.load_culture_months)
standard_running_mean_init = averages.BartlettAverager
numtempyears = 30
config={'rolling-years': 2}

def get_seasonal_index(region, culture_periods, seasons):
    if seasons == 'daily':
        plant = datetime.date(non_leap_year, culture_periods[region][0],1).timetuple().tm_yday
        if culture_periods[region][1] <= 12: 
            harvest_date = datetime.date(non_leap_year, culture_periods[region][1],1) + relativedelta(day=31)
            harvest = harvest_date.timetuple().tm_yday
        else:
            harvest_date = datetime.date(non_leap_year, culture_periods[region][1]-12,1) + relativedelta(day=31)
            harvest = harvest_date.timetuple().tm_yday + 365
    elif seasons == 'monthly':
        plant, harvest = culture_periods[region]
    return int(plant - 1), int(harvest - 1) 


for clim_scenario, clim_model, weatherbundle in weather.iterate_bundles(discoverer, **config):

    if (clim_model == 'CCSM4') and (clim_scenario == 'rcp85'):

        print clim_scenario, clim_model

        targetdir = os.path.join(outputdir, clim_scenario, clim_model)

        if only_missing and os.path.exists(os.path.join(targetdir, filename)):
            continue
            
        print targetdir
        if not os.path.exists(targetdir):
            os.makedirs(targetdir, 0775)

        # Initiate netcdf and dimensions, variables.
        rootgrp = Dataset(os.path.join(targetdir, filename), 'w', format='NETCDF4')
        rootgrp.description = "Growing season and 30-year Bartlett average temperatures."
        rootgrp.author = "Dylan Hogan"

        years = nc4writer.make_years_variable(rootgrp)
        regions = nc4writer.make_regions_variable(rootgrp, weatherbundle.regions, None)

        covar = rootgrp.createDimension('covar', len(covar_names))
        covars = rootgrp.createVariable('covars', str, ('covar',))
        covars.long_title = "Covariate name"

        #  Set variables.
        for kk in range(len(covar_names)):
            covars[kk] = covar_names[kk]

        yeardata = weatherbundle.get_years()
        years[:] = yeardata

        annual = rootgrp.createVariable("annual", 'f4', ('year', 'region', 'covar'))
        averaged = rootgrp.createVariable("averaged", 'f4', ('year', 'region', 'covar'))

        annualdata = np.zeros((len(yeardata), len(weatherbundle.regions), len(covar_names)))
        averageddata = np.zeros((len(yeardata), len(weatherbundle.regions), len(covar_names)))

        # Start up all the rms
        regiondata = []
        for ii in range(len(weatherbundle.regions)):
            covardata = []
            for jj in range(len(covar_names)):
                covardata.append(standard_running_mean_init([], numtempyears))
            regiondata.append(covardata)

        print "Processing years..."
        yy = 0
        for year, ds in weatherbundle.yearbundles():
            print "Push", year      
            regions = np.array(ds.region)
            ii = 0
            for region, subds in fast_dataset.region_groupby(ds, year, regions, {regions[ii]: ii for ii in range(len(regions))}):
                if region in culture_periods:
                    for kk in range(len(covar_names)):
                        plantii, harvestii = get_seasonal_index(region, culture_periods, seasons)
                        annual_calcs = lambda ds: np.mean(ds[clim_var].values[plantii:harvestii])
                        yearval = annual_calcs(subds)
                        annualdata[yy, ii, kk] = yearval
                        regiondata[ii][kk].update(yearval)
                        averageddata[yy, ii, kk] = regiondata[ii][kk].get()
                else:
                    print "Region {} not in growing season data set".format(region)
                ii += 1
            yy += 1

        annual[:, :, :] = annualdata
        averaged[:, :, :] = averageddata

        rootgrp.close()


