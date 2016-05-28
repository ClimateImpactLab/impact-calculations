import sys, os
import standard
from impacts import weather, effectset
from adaptation import adapting_curve

# e.g.,
# python -m generate.single /home/yuan/nasa_bcsd/grid2reg/CCSM4/tas_ndays/rcp85/tas_day_aggregated_rcp85_r1i1p1_CCSM4_ OECD\ Env-Growth,SSP3_v9_130325 /shares/gcp/outputs/diagnostics/areaagg/

get_model = effectset.get_model_server
pvals = effectset.ConstantPvals(.5)

weather_prefix = sys.argv[1]
econ_model_scenario = sys.argv[2].split(',')
targetdir = sys.argv[3]

standard.preload()

weather_template = weather_prefix + '%d.nc'
variable = weather.guess_variable(os.path.basename(weather_prefix))
futureyear1 = min(weather.available_years(weather_template))

try:
    pasttemplate = weather.guess_historical(weather_template)
    pastyear1 = min(weather.available_years(pasttemplate))

    weatherbundle = weather.UnivariatePastFutureWeatherBundle(pasttemplate, pastyear1, weather_template, futureyear1, variable, readncdf=weather.readncdf_binned)
except:
    print "Failed to connect to historical data."
    weatherbundle = weather.SingleWeatherBundle(weather_template, futureyear1, variable, readncdf=weather.readncdf_binned)

economicmodel = adapting_curve.SSPEconomicModel(econ_model_scenario[0], econ_model_scenario[1], [])
if not os.path.exists(targetdir):
    os.makedirs(targetdir)

effectset.make_pval_file(targetdir, pvals)
standard.produce(targetdir, weatherbundle, economicmodel, get_model, pvals, do_only="interpolation", do_farmers=True)
