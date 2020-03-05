import sys, os
sys.path.append('/home/dylanhogan/repositories/impact-calculations')
sys.path.append('/home/dylanhogan/repositories/impact-calculations/generate')
sys.path.append('/home/dylanhogan/repositories/impact-calculations/adaptation')
import numpy as np
from netCDF4 import Dataset
from . import weather, nc4writer
from openest.generate import fast_dataset
from impactlab_tools.utils import files
from impactcommon.math import averages
from datastore import irvalues
import datetime
from dateutil.relativedelta import relativedelta
from interpret.container import get_bundle_iterator
from climate.discover import discover_variable, discover_derived_variable, standard_variable

filename = 'maize_seasonaledd.nc4'
only_missing = False
non_leap_year = 2010

if filename == 'maize_seasonaltasmax.nc4':
    clim_var = ['tasmax']
    seasonal_filepath = "social/baselines/agriculture/world-combo-201710-growing-seasons-corn-1stseason.csv"
    func = np.mean

if filename == 'maize_seasonalpr.nc4':
    clim_var = ['pr']
    seasonal_filepath = "social/baselines/agriculture/world-combo-201710-growing-seasons-corn-1stseason.csv"
    func = np.mean

if filename == 'maize_seasonaledd.nc4':
    clim_var = ['gdd', 'kdd']
    seasonal_filepath = "social/baselines/agriculture/world-combo-201710-growing-seasons-corn-1stseason.csv"
    func = np.sum
    gdd_cutoff = 8
    kdd_cutoff = 31


config = {
    'climate': ['tasmax', 'pr', 'edd'],
    'covariates': ['seasonal' + c for c in clim_var],
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
    '''Parse growing season lengths in `culture_periods` and return ds indicies
    '''
    if timerate == 'daily':
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

def calculate_edd(ds, gdd_cutoff, kdd_cutoff):
    '''Calculate gdd and kdd from edd dataset
    '''
    kdd = ds.sel(refTemp=kdd_cutoff)['edd'].values
    gdd = kdd - ds.sel(refTemp=kdd_cutoff)['edd'].values
    out = fast_dataset.FastDataset({'kdd': (('time', 'region'), kdd),
                                    'gdd': (('time', 'region'), gdd)},
                                            {'time': ds.time, 'region': ds.region})
    return out

for clim_scenario, clim_model, weatherbundle in get_bundle_iterator(config):

    print(clim_scenario, clim_model)

    targetdir = os.path.join(outputdir, clim_scenario, clim_model)

    if only_missing and os.path.exists(os.path.join(targetdir, filename)):
        continue
        
    print(targetdir)
    if not os.path.exists(targetdir):
        os.makedirs(targetdir, 0o775)

    # Initiate netcdf and dimensions, variables.
    rootgrp = Dataset(os.path.join(targetdir, filename), 'w', format='NETCDF4')
    rootgrp.description = "Growing season and 30-year Bartlett average temperatures."
    rootgrp.author = "Dylan Hogan"

    years = nc4writer.make_years_variable(rootgrp)
    regions = nc4writer.make_regions_variable(rootgrp, weatherbundle.regions, None)

    covar = rootgrp.createDimension('covar', len(config['covariates']))
    covars = rootgrp.createVariable('covars', str, ('covar',))
    covars.long_title = "Covariate name"

    #  Set variables.
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
        if 'gdd' in clim_var or 'kdd' in clim_var:
            ds = calculate_edd(ds, gdd_cutoff, kdd_cutoff)
        ii = 0
        for region, subds in fast_dataset.region_groupby(ds, year, regions, {regions[ii]: ii for ii in range(len(regions))}):
            if region in culture_periods:
                plantii, harvestii = get_seasonal_index(region, culture_periods, config['timerate'])
                annual_calcs = lambda ds: func(ds[clim_var[kk]].values[plantii:harvestii])
                yearval = annual_calcs(subds)
                annualdata[yy, ii, kk] = yearval
                # Need this to preserve consistency with projection system...
                if year!=2014 or year!=2015:
                    regiondata[ii][kk].update(yearval)
                    averageddata[yy, ii, kk] = regiondata[ii][kk].get()
                if region == 'BGD.6.23.66.462':
                    print((plantii, harvestii))
                    print('annual', annualdata[yy, ii, kk])
                    print('avg', averageddata[yy, ii, kk])
            ii += 1
        yy += 1

    annual[:, :, :] = annualdata
    averaged[:, :, :] = averageddata

    rootgrp.close()


