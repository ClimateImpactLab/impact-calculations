import pdb
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

non_leap_year = 2010


config = {
    'climate': ['tasmax', 'tasmin','edd', 'pr', 'pr-poly-2 = pr-monthsum-poly-2'],
    'covariates': 'seasonaltasmin',
    'grid-weight': 'cropwt',
    'only-models': ['surrogate_GFDL-ESM2G_06'],
    'only-rcp': 'rcp85',
    'rolling-years': 2,
    'timerate': 'month',
    'within-season': "/shares/gcp/social/baselines/agriculture/world-combo-201710-growing-seasons-rice-1stseason.csv" }

    # config = {
    #     'climate': climates,
    #     'covariates': covars,
    #     'grid-weight': 'cropwt',
    #     'only-models': [climate_model],
    #     'only-rcp': rcp,
    #     'rolling-years': 2,
    #     'timerate': time_rate,
    #     'within-season': seasonal_filepath }

out=get_bundle_iterator(config)
print(list(out))

# if list(get_bundle_iterator(config))==[]:
#     print('the config file syntax is wrong')
#     exit()
