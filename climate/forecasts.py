from netCDF4 import Dataset

temp_path = "/shares/gcp/IRI/tas_aggregated_quantiles_2012-2016.nc"
prcp_path = "/shares/gcp/IRI/prcp_aggregated_quantiles_2012-2016.nc"
temp_zscore_path = "/shares/gcp/IRI/tas_zscores_aggregated_forecast_2012-2016Aug.nc"
prcp_zscore_path = "/shares/gcp/IRI/prcp_zscores_aggregated_forecast_2012-2016Aug.nc"
temp_climate_path = "/shares/gcp/IRI/tas_aggregated_climatology_1981-2010.nc"
prcp_climate_path = "/shares/gcp/IRI/prcp_aggregated_climatology_1981-2010.nc"

def readncdf_lastpred(filepath, variable, lead):
    """
    Return weather for each region for most recent prediction, of the given lead
    """
    rootgrp = Dataset(filepath, 'r', format='NETCDF4')
    weather = rootgrp.variables[variable][-1, lead, :]
    rootgrp.close()

    return maskmissing(weather)

def readncdf_allpred(filepath, variable, lead):
    """
    Yield weather for each region for each forecast month, of the given lead
    """
    rootgrp = Dataset(filepath, 'r', format='NETCDF4')
    alldata = rootgrp.variables[variable][:, :, :]
    rootgrp.close()

    for month in range(alldata.shape[0]):
        yield maskmissing(alldata[month, lead, :])

def maskmissing(weather):
    weather[weather > 1e10] = np.nan
    return weather
