import numpy as np
from netCDF4 import Dataset

temp_path = "/shares/gcp/climate/IRI/final_v2/tas_aggregated_forecast_Feb-Jun2017.nc"
prcp_path = "/shares/gcp/climate/IRI/final_v2/prcp_aggregated_forecast_Feb-Jun2017.nc"
temp_climate_path = "/shares/gcp/climate/IRI/tas_aggregated_climatology_1981-2010-new.nc"
prcp_climate_path = "/shares/gcp/climate/IRI/prcp_aggregated_climatology_1981-2010.nc"
#temp_zscore_path = "/shares/gcp/climate/IRI/tas_zscores_aggregated_forecast_2012-2017Mar.nc"
#prcp_zscore_path = "/shares/gcp/climate/IRI/prcp_zscores_aggregated_forecast_2012-2017Mar.nc"
#temp_normstddev_path = "/shares/gcp/climate/IRI/tas_normSTDDEV_aggregated_forecast.nc"
#prcp_normstddev_path = "/shares/gcp/climate/IRI/prcp_normSTDDEV_aggregated_forecast.nc"

def readncdf_lastpred(filepath, variable):
    """
    Return weather for each region for most recent prediction, of all leads
    """
    rootgrp = Dataset(filepath, 'r', format='NETCDF4')
    weather = rootgrp.variables[variable][-1, :, :]
    rootgrp.close()

    for ii in range(weather.shape[0]):
        weather[ii, :] = maskmissing(weather[ii, :])

    return weather

def readncdf_allpred(filepath, variable, lead):
    """
    Yield weather for each region for each forecast month, of the given lead
    """
    rootgrp = Dataset(filepath, 'r', format='NETCDF4')
    alldata = rootgrp.variables[variable][:, :, :]
    rootgrp.close()

    for month in range(alldata.shape[0]):
        yield maskmissing(alldata[month, lead, :])

def readncdf_allmonths(filepath, variable):
    """
    Return weather for each region for a variable with just 12 values
    """
    rootgrp = Dataset(filepath, 'r', format='NETCDF4')
    alldata = rootgrp.variables[variable][:, :]
    rootgrp.close()

    return alldata

def maskmissing(weather):
    weather[weather > 1e10] = np.nan
    return weather
