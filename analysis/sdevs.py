import operator
import xarray as xr
import numpy as np
from datastore import irregions
from climate import forecasts

regions = irregions.load_regions('hierarchy.csv', [])
ds = xr.open_dataset(forecasts.temp_sdev_climate_path)

bycountry = {}
bycountry2 = {}
num0 = {}
numsmall = {}
counts = {}
for ii in range(len(regions)):
    minds = np.min(ds.tas[:, ii].values)
    bycountry[regions[ii][:3]] = min(bycountry.get(regions[ii][:3], np.inf), minds)
    if np.max(ds.tas[:, ii].values) > 0:
        bycountry2[regions[ii][:3]] = min(bycountry2.get(regions[ii][:3], np.inf), np.min(ds.tas[:, ii].values[ds.tas[:, ii].values > 0]))
    if sum(ds.tas[:, ii].values == 0) > 0:
        num0[regions[ii][:3]] = num0.get(regions[ii][:3], 0) + 1
    if sum(ds.tas[:, ii].values < 1e-14) > 0:
        numsmall[regions[ii][:3]] = numsmall.get(regions[ii][:3], 0) + 1
    counts[regions[ii][:3]] = counts.get(regions[ii][:3], 0) + 1

countryorder = sorted(counts.items(), key=operator.itemgetter(1), reverse=True)
    
for country, county in countryorder:
    print "%s: %f, %g, %d, %d" % (country, bycountry[country], bycountry2.get(country, np.nan), num0.get(country, 0), numsmall.get(country, 0))
