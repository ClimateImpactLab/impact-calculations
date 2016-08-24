## XXX: This needs to be updated to use WeatherReader in climate/*.
## Remove all unclassed functions-- these are now in climate/forecast.py

import numpy as np
from netCDF4 import Dataset
from scipy.stats import norm
from impacts.weather import WeatherBundle

temp_path = "/shares/gcp/IRI/tas_aggregated_quantiles_2012-2016.nc"
prcp_path = "/shares/gcp/IRI/prcp_aggregated_quantiles_2012-2016.nc"
temp_climate_path = "/shares/gcp/IRI/tas_aggregated_climatology_1981-2010.nc"
prcp_climate_path = "/shares/gcp/IRI/prcp_aggregated_climatology_1981-2010.nc"

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
        yield alldata[month, lead, :]

class FirstForecastBundle(WeatherBundle):
    def __init__(self, filepath, hierarchy='hierarchy.csv'):
        super(FirstForecastBundle, self).__init__(hierarchy)
        self.filepath = filepath
        self.dependencies = [filepath]

        self.load_regions()
        self.load_metainfo(self.filepath, 'mean')

    def get_months(self):
        rootgrp = Dataset(self.filepath, 'r', format='NETCDF4')
        months = rootgrp.variables['S'][:]
        months_title = rootgrp.variables['S'].units
        rootgrp.close()

        return months, months_title

    def monthbundles(self, qval, maxyear=np.inf):
        months, months_title = self.get_months()
        meansgen = readncdf_allpred(self.filepath, "mean", 0)
        sdevsgen = readncdf_allpred(self.filepath, "stddev", 0)
        for month in months:
            yield month, norm.ppf(qval, meansgen.next(), sdevsgen.next())

class CombinedBundle(WeatherBundle):
    def __init__(self, bundles, hierarchy='hierarchy.csv'):
        super(CombinedBundle, self).__init__(hierarchy)
        self.bundles = bundles
        self.dependencies = set()
        for bundle in bundles:
            self.dependencies.update(bundle.dependencies)
        self.dependencies = list(self.dependencies)

        self.load_regions()
        self.version = bundles[0].version
        self.units = [bundle.units for bundle in bundles]

    def get_months(self):
        return self.bundles[0].get_months()

    def monthbundles(self, qval, maxyear=np.inf):
        months, months_title = self.get_months()
        iterators = [bundle.monthbundles(qval) for bundle in self.bundles]
        for month in months:
            results = []
            for iterator in iterators:
                monthii, result = iterator.next()
                assert month == monthii
                results.append(result)

            yield month, np.array(results)

if __name__ == '__main__':
    print np.mean(readncdf_lastpred(temp_path, "mean", 0))
    print np.mean(readncdf_lastpred(prcp_path, "mean", 0))

    bundle = FirstForecastBundle(temp_path)
    gener = bundle.monthbundles(.5)
    print np.mean(gener.next()[1])

    for monthvals in readncdf_allpred(temp_path, 'mean', 0):
        print monthvals[1000]
