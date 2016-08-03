import numpy as np
from netCDF4 import Dataset

temp_path = "/shares/gcp/IRI/tas_aggregated_quantiles_2012-2016.nc"
prcp_path = "/shares/gcp/IRI/prcp_aggregated_quantiles_2012-2016.nc"

def readncdf_firstoflast(filepath, variable):
    """
    Return yyyyddd, weather
    """
    rootgrp = Dataset(filepath, 'r', format='NETCDF4')
    weather = rootgrp.variables[variable][-1, 0, :]
    rootgrp.close()

    return weather

print np.mean(readncdf_firstoflast(temp_path, "mean"))
print np.mean(readncdf_firstoflast(prcp_path, "mean"))
