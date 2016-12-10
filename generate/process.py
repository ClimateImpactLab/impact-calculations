import os, re, csv
import weather, server, effectset
from openest.generate import retrieve
from health.mortality_allages import prepare
from datastore import library

single_weather_root = "/shares/gcp/BCSD/grid2reg/cmip/rcp85"
# subfile like tasmin/tasmin_day_aggregated_rcp85_r1i1p1_CCSM4_2020.nc

weatherbundle = weather.UnivariateWeatherBundle(os.path.join(taspath, "tas_day_aggregated_rcp85_r1i1p1_CCSM4_%d.nc"), range(2006, 2100), 'tas')

calculation, dependencies = prepare(effectset.PvalsConstantDictionary(.5), effectset.get_model_server, library.get_data)
effectset.write_ncdf("HealthMortalityAllAges", weatherbundle, calculation, "Mortality for all ages.  See https://bitbucket.org/ClimateImpactLab/socioeconomics/wiki/ModelDescriptions#rst-header-acra-mortality-deschenes-greenstone-2011 for more information.", dependencies)
