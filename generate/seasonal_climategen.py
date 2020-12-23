#!/usr/bin/env python3
"""Functions to generate annual and moving averages seasonal monthly climate variables. 
Follows the projection system methods and parameters.
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

def is_longrun_climate(var):
    return var in ['seasonaltasmax','seasonalpr']

def get_suffix_triangle():

    """ data structure that allocates a growing season month to a subseason. 

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

def get_subseasonal_index(subseason, suffix_triangle, growing_season_length):

    """
    Returns
    -------
    A list with the indexes of the elements of `suffix_triangle`[`growing_season_length`] that match `subseason`.
    If the subseason doesn't fall in the growing season, the returned list is empty. 
    """

    return [i for i,x in enumerate(suffix_triangle[growing_season_length-1]) if x==subseason]

def get_seasonal_index(region, culture_periods, subseason=None, suffix_triangle=None, transform_index=True):

    """retrieves integers indicating  the start and end of the growing season, or
    the start and end of a subseason of that growing season for a given region. It can return 'usable' indexes -- see the description
    of `transform_index`, 

    This function assumes the time rate used to generate culture_periods is 'month'. 

    Parameters
    ----------
    region : str
    culture_periods : dict : a [region] dictionary with start and end month of growing season for each region.
    subseason : None or str (the name of the season from which to build a growing season subset). 
    suffix_triangle : None or (required) list-of-list-of-strings if subseason!=None. Allocates growing season months to subseasons. It uses a predefined 'suffix-triangle', which
    properties are defined in the adaptation.curvegen.SeasonalTriangleCurveGenerator class.
    transform_index: if True, subtract one to first returned value and subtract and add one to second returned value. Details : 
       useful if returned values are passed as start and and of a range of indexes to subset monthly weather data, which implies: 
        - start and end are used as indexes of a list - therefore both must be shifted by minus one. 
        - in addition, they are used in range(start, stop), which gives the span of start:stop, stop being excluded. Hence should add one to the returned value.

    Returns
    -------
    A tuple, that is either :
        - first_month, last_month if transform_index=False
        - (first_month-1), (last_month -1 + 1) if transform_index=True. 
            where first_month and last_month are the first and last month of the growing season or 
            of the subseason of the growing season if subseason=None and the subseason exist in the growing season per the `suffix_triangle` definition.
        - None,None if subseason!=None and the subseason does not exist per the subseasons definition.
    """

    plant, harvest = culture_periods[region] 
    span = range(plant, harvest+1) #full range from start to end included.

    if subseason!=None:
        growing_season_length = len(span)
        assert suffix_triangle!=None, "if you pass a subseason, you need to pass a suffix_triangle"
        subseason_indexes = get_subseasonal_index(subseason, suffix_triangle, growing_season_length)
        if len(subseason_indexes)==0:
            return (None, None)
        span = [span[i] for i in subseason_indexes]

    plant_index = span[0]
    harvest_index = span[len(span)-1] #for clarity of what's happening. 

    if transform_index:
        plant_index = plant_index-1
        harvest_index = harvest_index-1+1

    return plant_index, harvest_index


def get_monthbin_index(region, culture_periods, clim_var, monthbin, subseason=None, suffix_triangle=None):

    """Allocates the months of a region's growing season to a given precipitation bin. Can also allocate months of a subseason of the growing season 
    if there is no actual binning (only one singe bin). 

        Parameters
        ----------
        region : str
        culture_periods : dict[region]
        clim_var : str
            identifies a precipitation bin. 
            it requires that the last character of the str is the bin number (hence coercible to an integer).
            it requires that this last character is inferior or equal to the number of elements of monthbin.
        monthbin : list of int. 
            the number of elements of the list is interpreted as the number of precipitation bins.
            it requires that the sum of the elements should be equal to 24 (2 rolling years are used). 
        subseason : see get_seasonal_index().
            if !=None, requires suffix_triangle!=None & len(montbin)==1. 
        suffix_triangle : see get_seasonal_index()
            if !=None, requires subseason!=None


        Returns
        -------
        tuple of int.
            the tuple contains two elements, the index to catch the first month of the precipitation bin in the weather data, and the index to catch the last. 
            values are compatible with the indexing that will be performed, see get_seasonal_index(). 
    
    """
    try:
        int(clim_var[-1])
    except ValueError:
        print("Error : the last character of clim_var can't be coerced into an integer")
    assert int(clim_var[-1])<=len(monthbin), print("Error : the last character of clim_var, which is supposed to identify a bin, is greater than the number of bins.")
    assert sum(monthbin)==24, print("Error : the sum of the monthbin list should be equal to 24")

    if subseason!=None or suffix_triangle!=None:
        assert subseason!=None and suffix_triangle!=None, print("you need to pass subseason and suffix_triangle together")
        assert len(monthbin)==1, print("if you pass a subseason, you can't request a binning. I can't handle that.")
    
    plant, harvest = get_seasonal_index(region, culture_periods, subseason, suffix_triangle, transform_index=False)

    bindex = int(clim_var[-1]) - 1
    allmonths = [*range(plant, harvest+1)]
    mlist = []
    for x in monthbin:
        mlist.append(allmonths[0:x])
        del allmonths[:x]
    if mlist[bindex]:
        out = int(mlist[bindex][0]-1), int(mlist[bindex][-1])
    else:
        out = 0, 0

    return out

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


def get_seasonal(crop, var, climate_model, rcp, targetdir=None):

    """Collapses weather data to obtain seasonal calculations.

    Parameters
    ----------
    crop : str
        'crop' name. One of ['maize', 'rice', 'soy', 'cassava','sorghum','cotton', 'wheat-spring','wheat-winter-fall','wheat-winter-winter', 'wheat-winter-summer']
    culture_periods : dict[region]
    clim_var : str
        one of ['seasonaledd', 'seasonalpr', 'seasonaltasmax', 'seasonaltasmin', 'monthbinpr']
    climate_model : str
    rcp : str 
    """
    only_missing = False
    gdd_cutoff, kdd_cutoff, monthbin = None, None, None
    time_rate='month'

    if crop.find('wheat-winter')!=-1 and not is_longrun_climate(var):
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

    assert crop in ['maize', 'rice', 'soy', 'cassava','sorghum','cotton', 'wheat-spring','wheat-winter-fall','wheat-winter-winter', 'wheat-winter-summer'], print('unknown crop')
    assert var in ['seasonaltasmax', 'seasonalpr', 'seasonaltasmin', 'monthbinpr', 'seasonaledd'], print('unknown variable')

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

        if targetdir==None:
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
            if gdd_cutoff!=None and kdd_cutoff!=None:
                ds = calculate_edd(ds, gdd_cutoff, kdd_cutoff)
            ii = 0
            for region, subds in fast_dataset.region_groupby(ds, year, regions, {regions[ii]: ii for ii in range(len(regions))}):
                if region in culture_periods:
                    for kk in range(len(config['covariates'])):
                        # Get indices for (1) month of season bin or (2) full growing season.
                        if monthbin:
                            plantii, harvestii = get_monthbin_index(region, culture_periods, config['covariates'][kk], monthbin)
                        else:
                            if subseason==None:
                                plantii, harvestii = get_seasonal_index(region, culture_periods)
                            else: 
                                plantii, harvestii = get_seasonal_index(region, culture_periods, subseason, get_suffix_triangle())

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