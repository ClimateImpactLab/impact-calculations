import numpy as np
from netCDF4 import Dataset

temp_path = "/shares/gcp/IRI/tas_aggregated_quantiles_2012-2016.nc"
prcp_path = "/shares/gcp/IRI/prcp_aggregated_quantiles_2012-2016.nc"

def readncdf_lastpred(filepath, variable, lead):
    """
    Return weather for each region for most recent prediction, of the given lead
    """
    rootgrp = Dataset(filepath, 'r', format='NETCDF4')
    weather = rootgrp.variables[variable][-1, lead, :]
    rootgrp.close()

    return weather

print np.mean(readncdf_firstoflast(temp_path, "mean", 0))
print np.mean(readncdf_firstoflast(prcp_path, "mean", 0))

class ForecastBundle(object):
    def __init__(self, filepath):
        self.filepath = filepath

    def monthbundles(self, maxyear=np.inf, qval):
        for lead in range(5):
            means = readncdf_lastpred(self.filepath, "mean", lead)
            sdevs = readncdf_lastpred(self.filepath, "stddev", lead)
            yield norm.ppf(qval, means, sdevs)
