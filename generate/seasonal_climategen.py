#!/usr/bin/env python3
"""Generates long-run growing-season averages of climate variables.

Config parameters are mostly consistent with the impact-calculations arguments.
Outputs netCDF `filename` to `/shares/gcp/outputs/temps/{RCP}/{GCM}`

`get_seasonal_index` and `get_monthbin_index` are helper functions for defining
the relevant months within a year. `calculate_edd` transforms the edd dataset
into gdds and kdds.

first argument : filename 
second argument : climate model
third argument : rcp
"""

import sys, os
import datetime
import numpy as np
from netCDF4 import Dataset
from generate import weather, nc4writer
from openest.generate import fast_dataset
from impactcommon.math import averages
from datastore import irvalues
from dateutil.relativedelta import relativedelta
from interpret.container import get_bundle_iterator
import multiprocessing
from itertools import product
import pdb 

non_leap_year = 2010

def get_suffix_triangle():

    """ allocates a growing season month to a subseason. It uses a predefined 'suffix-triangle', which
    properties are defined in the adaptation.curvegen.SeasonalTriangleCurveGenerator class.

    Returns
    -------
    a list-of-list ('suffix-triangle')
    """

    suffix_triangle = [ ['summer'], #1
    ['summer', 'summer'], #2 
    ['summer', 'summer', 'summer'], #3
    ['summer', 'summer', 'summer', 'summer'], #4
    ['summer', 'summer', 'summer', 'summer', 'summer'], #5
    ['fall', 'summer', 'summer', 'summer', 'summer', 'summer'], #6
    ['fall', 'fall', 'summer', 'summer', 'summer', 'summer', 'summer'], #7
    ['fall', 'fall', 'winter', 'summer', 'summer', 'summer', 'summer', 'summer'], #8
    ['fall', 'fall', 'winter', 'winter', 'summer', 'summer', 'summer', 'summer', 'summer'], #9
    ['fall', 'fall', 'winter', 'winter', 'winter', 'summer', 'summer', 'summer', 'summer', 'summer'], #10
    ['fall', 'fall', 'winter', 'winter', 'winter', 'winter', 'summer', 'summer', 'summer', 'summer', 'summer'], #11
    ['fall', 'fall', 'winter', 'winter', 'winter', 'winter', 'winter', 'summer', 'summer', 'summer', 'summer', 'summer'] #12
    ]

    return suffix_triangle

def get_seasonal_index(region, culture_periods, subseason=None):

    """retrieves start and end of the growing season, or a seasonal subset within the growing season for a given region.
    Handles monthly time rate only. To preserve consistency with the projection system (adaptation.SeasonalWeatherCovariator), 
    a given growing season (as described in the growing season file by planting and harvesting date) is extended by one unit 
    in its beginning. E.g. months 1,2,3,4,5 growing season becomes months 0,1,2,3,4,5 growing season.

    Parameters
    ----------
    region : str
    culture_periods : dict : a [region] dictionary with start and end month of growing season for each region.
    subseason : None or str (the name of the season from which to build a growing season subset). 

    Returns
    -------
    Either : 
        - a tuple, that is itslef either the start and end month of the growing season, 
    or the start and end of a seasonal subset of that growing season. A unit is subtracted from the start date (see above). If the remaining
    list is a singleton, the tuple returned has two identical elements (the given month).
        - or None, if the subseason requested does not exist in that region as per the 'suffix-triangle' definition.
    """

    # if timerate == 'day':
    #     plant = datetime.date(non_leap_year, culture_periods[region][0],1).timetuple().tm_yday
    #     if culture_periods[region][1] <= 12: 
    #         harvest_date = datetime.date(non_leap_year, culture_periods[region][1],1) + relativedelta(day=31)
    #         harvest = harvest_date.timetuple().tm_yday
    #     else:
    #         harvest_date = datetime.date(non_leap_year, culture_periods[region][1]-12,1) + relativedelta(day=31)
    #         harvest = harvest_date.timetuple().tm_yday + 365

    plant, harvest = culture_periods[region] 
    span = range(plant-1, harvest+1) #get the full range from start to end included, and extend the start

    if subseason!=None:
        fullseasonlength = len(span)
        suffix_triangle = get_suffix_triangle()
        subseason_indexes = [i for i,x in enumerate(suffix_triangle[fullseasonlength-1]) if x==subseason] #obtain position of subseason in growing season months
        if len(subseason_indexes)==0: 
            return (None,None)
        else: 
            span = [span[i] for i in subseason_indexes]

    if len(span)==1:
        return span[0], span[0]
    else:
        return span[0], span[len(span)-1]


def get_monthbin_index(region, culture_periods, clim_var, monthbin):

    """Allocates growing seasons to months-of-season precip bins. 

    Parameters
    ----------
    region : str
    culture_periods : dict[region]
    clim_var : 
    monthbin : 

    Returns
    -------
    
    
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


def get_seasonal(crop, var, climate_model, rcp):

    """Collapses weather data to obtain seasonal calculations.

    Parameters
    ----------
    crop : str
        crop name
    culture_periods : dict[region]
    clim_var : str
        one of ['seasonaledd', 'seasonalpr', 'seasonaltasmax', 'seasonaltasmin', 'monthbinpr']
    climate_model : str
    rcp : str 
    
    """
    only_missing = False
    gdd_cutoff, kdd_cutoff, monthbin = None, None, None
    time_rate='month'

    if crop.find('wheat-winter')!=-1:
        subseason=crop.replace('wheat-winter-', '')
    else:
        subseason=None

    print('Processing arguments')

    seasons = {
        'maize':'world-combo-201710-growing-seasons-corn-1stseason',
        'rice':'world-combo-201710-growing-seasons-rice-1stseason',
        'soy':'world-combo-201710-growing-seasons-soy',
        'cassava':'world-combo-202004-growing-seasons-cassava',
        'sorghum':'world-combo-202004-growing-seasons-sorghum',
        'cotton':'world-combo-202004-growing-seasons-cotton',
        'wheat-spring':'world-combo-202004-growing-seasons-wheat-spring',
        'wheat-winter-fall':'world-combo-202004-growing-seasons-wheat-winter',
        'wheat-winter-winter':'world-combo-202004-growing-seasons-wheat-winter',
        'wheat-winter-summer':'world-combo-202004-growing-seasons-wheat-winter'
    }

    bins = {
        'maize':[1, 3, 24-1-3],
        'rice':[2, 3, 24-2-3],
        'soy':[1, 1, 2, 24-1-1-2],
        'cassava':[24],
        'sorghum':[1,2,24-1-2],
        'cotton':[24],
        'wheat-spring':[24],
        'wheat-winter-fall':[24],
        'wheat-winter-winter':[24],
        'wheat-winter-summer':[24],
    }

    eddkinks = {
        'maize':[8,31],
        'rice':[14,30],
        'soy':[8,31],
        'cassava':[10,29],
        'sorghum':[15,31],
        'cotton':[10,29],
        'wheat-spring':[1,11],
        'wheat-winter-fall':[0,5],
        'wheat-winter-winter':[1,17],
        'wheat-winter-summer':[1,11]
    }

    if var == 'seasonaltasmax':
        # Relevant climate variables.
        clim_var = ['tasmax'] 
        # Within-year aggregation.
        func = np.mean 
        # Covariate prefix.
        covars = ['seasonal' + c for c in clim_var] 

    if var == 'seasonalpr':
        clim_var = ['pr']
        func = np.mean
        covars = ['seasonal' + c for c in clim_var]

    if var == 'seasonaledd':
        clim_var = ['gdd', 'kdd']
        func = np.sum
        gdd_cutoff = eddkinks[crop][0]
        kdd_cutoff = eddkinks[crop][1]
        covars = ['seasonal' + c for c in clim_var]

    if var == 'seasonaltasmin':
        # Relevant climate variables.
        clim_var = ['tasmin'] 
        # Within-year aggregation.
        func = np.sum 
        # Covariate prefix.
        covars = ['seasonal' + c for c in clim_var] 

    if var == 'monthbinpr':
        clim_var = ['pr', 'pr-poly-2']
        func = np.sum
        # Months of growing-season bins with extended final bin.
        monthbin = bins[crop] 
        clim_var = [c + '_bin' + str(m+1) for m in range(len(monthbin)) for c in clim_var]
        covars = ['monthbin' + c for c in clim_var]


    seasonal_filepath = "social/baselines/agriculture/" + seasons[crop] + '.csv' 
    filename = crop + '_' + var + '.nc4'

    if time_rate == 'day':
        climates = ['tasmax', 'tasmin','pr']
    else: 
        climates = ['tasmax', 'tasmin','edd', 'pr', 'pr-poly-2 = pr-monthsum-poly-2']

    config = {
        'climate': climates,
        'covariates': covars,
        'grid-weight': 'cropwt',
        'only-models': [climate_model],
        'only-rcp': rcp,
        'rolling-years': 2,
        'timerate': time_rate,
        'within-season': seasonal_filepath }
    
    if list(get_bundle_iterator(config))==[]:
        print('the config file syntax is wrong')
        exit()

    outputdir = '/shares/gcp/outputs/temps'
    culture_periods = irvalues.get_file_cached(config['within-season'], irvalues.load_culture_months)
    standard_running_mean_init = averages.BartlettAverager
    numtempyears = 30

    print('Starting bundle iterator')

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
        rootgrp.author = "Emile Tenezakis"

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
                            plantii, harvestii = get_seasonal_index(region, culture_periods, subseason)
                        cv = clim_var[kk].split('_')[0]

                        # Perform within-year collapse and update long-run averager.
                        if plantii==None and harvestii==None:
                            yearval=0
                        else:
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



get_seasonal(crop='wheat-winter-winter', var='seasonaledd', climate_model='CCSM4', rcp='rcp85')