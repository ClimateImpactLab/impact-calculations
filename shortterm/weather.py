import numpy as np
from netCDF4 import Dataset
from scipy.stats import norm

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

class ForecastBundle(object):
    def __init__(self, filepath):
        self.filepath = filepath

    def monthbundles(self, qval, maxyear=np.inf):
        for lead in range(5):
            means = readncdf_lastpred(self.filepath, "mean", lead)
            sdevs = readncdf_lastpred(self.filepath, "stddev", lead)
            yield norm.ppf(qval, means, sdevs)

if __name__ == '__main__':
    print np.mean(readncdf_lastpred(temp_path, "mean", 0))
    print np.mean(readncdf_lastpred(prcp_path, "mean", 0))

    bundle = ForecastBundle(temp_path)
    gener = bundle.monthbundles(.5)
    print np.mean(gener.next())
