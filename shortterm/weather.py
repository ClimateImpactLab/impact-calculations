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

def readncdf_allpred(filepath, variable, lead):
    """
    Yield weather for each region for each forecast month, of the given lead
    """
    rootgrp = Dataset(filepath, 'r', format='NETCDF4')
    alldata = rootgrp.variables[variable][:, :, :]
    rootgrp.close()

    for month in range(alldata.shape[0]):
        yield rootgrp.variables[variable][month, lead, :]

class FirstForecastBundle(object):
    def __init__(self, filepath):
        self.filepath = filepath

    def monthbundles(self, qval, maxyear=np.inf):
        meansgen = readncdf_allpred(self.filepath, "mean", 0)
        sdevsgen = readncdf_allpred(self.filepath, "stddev", 0)
        for means in meansgen:
            yield norm.ppf(qval, means, sdevsgen.next())

if __name__ == '__main__':
    print np.mean(readncdf_lastpred(temp_path, "mean", 0))
    print np.mean(readncdf_lastpred(prcp_path, "mean", 0))

    bundle = ForecastBundle(temp_path)
    gener = bundle.monthbundles(.5)
    print np.mean(gener.next())
