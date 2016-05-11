import csv
import health
from helpers import files
import helpers.header as headre
from impacts import weather, effectset
import utils

taspath = "/shares/gcp/BCSD/grid2reg/cmip/rcp85/tas"
do_median = True

dependencies = []

# Loop through baseline temperatures
weatherbundle = weather.UnivariateWeatherBundle(os.path.join(taspath, "tas_day_aggregated_rcp85_r1i1p1_CCSM4_%d.nc"), range(2006, 2100), 'tas', 'hierarchy-new.csv')

weather_version, weather_units = weather.readmeta(os.path.join(taspath, "tas_day_aggregated_rcp85_r1i1p1_CCSM4_2010.nc"), 'tas')
dependencies.append(weather_version)

weatherbundle, calculation, curve, baseline_get_predictors = health.prepare(taspath, do_median, dependencies)

# Output baselines
with open(files.datapath('adaptation/outputs/baselines.csv'), 'w') as fp:
    headre.write(fp, "Median interpolated bins for each GCP region, using baseline temperatures.",
                 headre.dated_version('MORTALITY_SPACE'), dependencies,
                 {'region': ('GCP region key', 'str'),
                  'avg_temp': ('Average temperature', 'deg C'),
                  'bin_X_Y': ('Level of effect for days with temperatures between X and Y', 'log mortality rate / day')})
    writer = csv.writer(fp, lineterminator='\n')
    writer.writerow(['region', 'avg_temp'] + [utils.bounds_to_string('bin', curve.beta_generator.xxlimits[ii], curve.beta_generator.xxlimits[ii+1]) for ii in range(len(curve.beta_generator.xxlimits) - 1)])

    for region, avg_temp in weatherbundle.baseline_average(2015):
        print region
        writer.writerow([region, avg_temp] + curve.beta_generator.get_curve([avg_temp]).yy)

# Generate results
effectset.write_ncdf("HealthMortalityAllAges", weatherbundle, calculation, baseline_get_predictors, "Mortality for all ages, with interpolation and adaptation.", dependencies)

# Output endlines
with open(files.datapath('adaptation/outputs/endlines.csv'), 'w') as fp:
    headre.write(fp, "Median interpolated bins for each GCP region, after a century of adaptation.",
                 headre.dated_version('MORTALITY'), dependencies,
                 {'region': ('GCP region key', 'str'),
                  'avg_temp': ('Average temperature', 'deg C'),
                  'bin_X_Y': ('Level of effect for days with temperatures between X and Y', 'log mortality rate / day')})
    writer = csv.writer(fp, lineterminator='\n')
    writer.writerow(['region', 'avg_temp'] + [utils.bounds_to_string('bin', curve.beta_generator.xxlimits[ii], curve.beta_generator.xxlimits[ii+1]) for ii in range(len(curve.beta_generator.xxlimits) - 1)])

    for region, avg_temp in weatherbundle.baseline_average(2015):
        print region
        writer.writerow([region, avg_temp] + curve.curr_curve[region].yy)
