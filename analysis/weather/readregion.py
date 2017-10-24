import numpy as np
from generate import weather
from climate.discover import discover_tas_binned

bundle_iterator = weather.iterate_bundles(discover_tas_binned('/shares/gcp/climate/BCSD/aggregation/cmip5_bins/IR_level'))

region = "IND.33.542.2153"

for scenario, model, bundle in bundle_iterator:
    if scenario == 'rcp85' and model == 'CCSM4':
        rr = bundle.regions.index(region)
        for year, ds in bundle.yearbundles():
            print year, np.sum(ds.variables[0][:, rr, :], axis=0)
