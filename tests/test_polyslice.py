import numpy as np
from impactlab_tools.utils import files
from openest.generate.weatherslice import YearlyWeatherSlice
from climate.discover import discover_variable, discover_derived_variable, discover_convert
from generate import weather, loadmodels

def time_convert(times):
    allyears = np.array(map(int, np.array(times) // 1000))
    years, indexes = np.unique(allyears, return_index=True)
    return allyears[np.sort(indexes)] # make sure in order

bundle_iterator = weather.iterate_combined_bundles(discover_convert(discover_variable(files.sharedpath('climate/BCSD/aggregation/cmip5/IR_level'), 'tas', withyear=True, rcp_only='rcp85'),
                                                                    time_convert, YearlyWeatherSlice.convert),
                                                   discover_derived_variable(files.sharedpath('climate/BCSD/aggregation/cmip5/IR_level'), 'tas', 'power2', withyear=False, rcp_only='rcp85'),
                                                   discover_derived_variable(files.sharedpath('climate/BCSD/aggregation/cmip5/IR_level'), 'tas', 'power3', withyear=False, rcp_only='rcp85'))

clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel = loadmodels.single(bundle_iterator)

for weatherslice in weatherbundle.yearbundles():
    print weatherslice.times[:10]
    print weatherslice.get_years()[:10]
    print weatherslice.weathers.shape
    print weatherslice.weathers[0, 0, :]
    break

