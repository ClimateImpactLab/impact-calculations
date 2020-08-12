"""Generates long-run growing-season averages of climate variables.

Config parameters are mostly consistent with the impact-calculations arguments.
Outputs netCDF `filename` to `/shares/gcp/outputs/temps/{RCP}/{GCM}`

`get_seasonal_index` and `get_monthbin_index` are helper functions for defining
the relevant months within a year. `calculate_edd` transforms the edd dataset
into gdds and kdds.

"""

import sys, os
import datetime
import numpy as np
from netCDF4 import Dataset
from . import weather, nc4writer
from openest.generate import fast_dataset
from impactcommon.math import averages
from datastore import irvalues
from dateutil.relativedelta import relativedelta
from interpret.container import get_bundle_iterator

filename = 'rice_seasonaltasmax.nc4'
only_missing = False
non_leap_year = 2010
gdd_cutoff, kdd_cutoff, monthbin = None, None, None

if filename == 'maize_seasonaltasmax.nc4':
    clim_var = ['tasmax'] # Relevant climate variables.
    seasonal_filepath = "social/baselines/agriculture/world-combo-201710-growing-seasons-corn-1stseason.csv"
    func = np.mean # Within-year aggregation.
    covars = ['seasonal' + c for c in clim_var] # Covariate prefix.

if filename == 'maize_seasonalpr.nc4':
    clim_var = ['pr']
    seasonal_filepath = "social/baselines/agriculture/world-combo-201710-growing-seasons-corn-1stseason.csv"
    func = np.mean
    covars = ['seasonal' + c for c in clim_var]

if filename == 'maize_seasonaledd.nc4':
    clim_var = ['gdd', 'kdd']
    seasonal_filepath = "social/baselines/agriculture/world-combo-201710-growing-seasons-corn-1stseason.csv"
    func = np.sum
    gdd_cutoff = 8
    kdd_cutoff = 31
    covars = ['seasonal' + c for c in clim_var]

if filename == 'maize_monthbinpr.nc4':
    clim_var = ['pr', 'pr-poly-2']
    seasonal_filepath = "social/baselines/agriculture/world-combo-201710-growing-seasons-corn-1stseason.csv"
    func = np.sum
    monthbin = [1, 3, 24-1-3] # Months of growing-season bins with extended final bin.
    clim_var = [c + '_bin' + str(m+1) for m in range(len(monthbin)) for c in clim_var]
    covars = ['monthbin' + c for c in clim_var]

if filename == 'rice_seasonaltasmax.nc4':
    clim_var = ['tasmax'] # Relevant climate variables.
    seasonal_filepath = "social/baselines/agriculture/world-combo-201710-growing-seasons-rice-1stseason.csv"
    func = np.mean # Within-year aggregation.
    covars = ['seasonal' + c for c in clim_var] # Covariate prefix.

config = {
    'climate': ['tasmax'], # ['tasmax', 'edd', 'pr', 'pr-poly-2 = pr-monthsum-poly-2'],
    'covariates': covars,
    'grid-weight': 'cropwt',
    'only-models': ['CCSM4'],
    'only-rcp': 'rcp85',
    'rolling-years': 2,
    'timerate': 'month',
    'within-season': seasonal_filepath }

outputdir = '/shares/gcp/outputs/temps'
culture_periods = irvalues.get_file_cached(config['within-season'], irvalues.load_culture_months)
standard_running_mean_init = averages.BartlettAverager
numtempyears = 30

def get_seasonal_index(region, culture_periods, timerate):
    """Parse growing season lengths in `culture_periods` and return ds indices.
    """
    if timerate == 'day':
        plant = datetime.date(non_leap_year, culture_periods[region][0],1).timetuple().tm_yday
        if culture_periods[region][1] <= 12: 
            harvest_date = datetime.date(non_leap_year, culture_periods[region][1],1) + relativedelta(day=31)
            harvest = harvest_date.timetuple().tm_yday
        else:
            harvest_date = datetime.date(non_leap_year, culture_periods[region][1]-12,1) + relativedelta(day=31)
            harvest = harvest_date.timetuple().tm_yday + 365
    elif timerate == 'month':
        plant, harvest = culture_periods[region]
    return int(plant - 1), int(harvest) 

def get_monthbin_index(region, culture_periods, clim_var, monthbin):
    """Allocates growing seasons to months-of-season precip bins.
    """
    plant, harvest = culture_periods[region]
    bindex = int(clim_var[-1]) - 1
    allmonths = [*range(plant, harvest+1)]
    mlist = []
    for x in monthbin:
        mlist.append(allmonths[0:x])
        del allmonths[:x]
    if mlist[bindex]:
        return int(mlist[bindex][0]-1), int(mlist[bindex][-1])
    else:
        return 0, 0

def calculate_edd(ds, gdd_cutoff, kdd_cutoff):
    """Calculate gdd and kdd from edd dataset.
    """
    kdd = ds.sel(refTemp=kdd_cutoff)['edd'].values
    gdd = ds.sel(refTemp=gdd_cutoff)['edd'].values - kdd
    out = fast_dataset.FastDataset({
        'kdd': (('time', 'region'), kdd),
        'gdd': (('time', 'region'), gdd)},
        {'time': ds.time, 'region': ds.region})
    return out

for clim_scenario, clim_model, weatherbundle in get_bundle_iterator(config):

    targetdir = os.path.join(outputdir, clim_scenario, clim_model)

    if only_missing and os.path.exists(os.path.join(targetdir, filename)):
        print("File exists. Exiting...")
        continue
        
    print("Generating " + filename + " in " + targetdir)
    if not os.path.exists(targetdir):
        os.makedirs(targetdir, 0o775)

    # Initiate netcdf and dimensions, variables.
    rootgrp = Dataset(os.path.join(targetdir, filename), 'w', format='NETCDF4')
    rootgrp.description = "Growing season and 30-year Bartlett average climate variables."
    rootgrp.author = "Dylan Hogan"

    years = nc4writer.make_years_variable(rootgrp)
    regions = nc4writer.make_regions_variable(rootgrp, weatherbundle.regions, None)

    covar = rootgrp.createDimension('covar', len(config['covariates']))
    covars = rootgrp.createVariable('covars', str, ('covar',))
    covars.long_title = "Covariate name"

    # Set variables.
    for kk in range(len(config['covariates'])):
        covars[kk] = config['covariates'][kk]

    yeardata = weatherbundle.get_years()
    years[:] = yeardata

    annual = rootgrp.createVariable("annual", 'f4', ('year', 'region', 'covar'))
    averaged = rootgrp.createVariable("averaged", 'f4', ('year', 'region', 'covar'))

    annualdata = np.zeros((len(yeardata), len(weatherbundle.regions), len(config['covariates'])))
    averageddata = np.zeros((len(yeardata), len(weatherbundle.regions), len(config['covariates'])))

    # Start up all the rms
    regiondata = []
    for ii in range(len(weatherbundle.regions)):
        covardata = []
        for jj in range(len(config['covariates'])):
            covardata.append(standard_running_mean_init([], numtempyears))
        regiondata.append(covardata)

    print("Processing years...")
    yy = 0
    for year, ds in weatherbundle.yearbundles():
        print("Push", year)
        regions = np.array(ds.coords["region"])
        if gdd_cutoff and kdd_cutoff:
            ds = calculate_edd(ds, gdd_cutoff, kdd_cutoff)
        ii = 0
        for region, subds in fast_dataset.region_groupby(ds, year, regions, {regions[ii]: ii for ii in range(len(regions))}):
            if region in culture_periods:
                for kk in range(len(config['covariates'])):

                    # Get indices for (1) month of season bin or (2) full growing season.
                    if monthbin:
                        plantii, harvestii = get_monthbin_index(region, culture_periods, config['covariates'][kk], monthbin)
                    else:
                        plantii, harvestii = get_seasonal_index(region, culture_periods, config['timerate'])
                    cv = clim_var[kk].split('_')[0]

                    # Perform within-year collapse and update long-run averager.
                    annual_calcs = lambda ds: func(ds[cv].values[plantii:harvestii])
                    yearval = annual_calcs(subds)
                    annualdata[yy, ii, kk] = yearval
                    # Need this to preserve consistency with projection system.
                    if year!=2014 and year!=2015:
                        regiondata[ii][kk].update(yearval)
                    averageddata[yy, ii, kk] = regiondata[ii][kk].get()
            ii += 1
        yy += 1

    annual[:, :, :] = annualdata
    averaged[:, :, :] = averageddata

    rootgrp.close()
