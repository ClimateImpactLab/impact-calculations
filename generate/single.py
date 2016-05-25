import sys, os
import standard
from impacts import weather, effectset
from adaptation import adapting_curve

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

    weatherbundle = weather.UnivariatePastFutureWeatherBundle(pasttemplate, pastyear1, weather_template, futureyear1, variable)
except:
    print "Failed to connect to historical data."
    weatherbundle = weather.SingleWeatherBundle(weather_template, futureyear1, variable)

economicmodel = adapting_curve.SSPEconomicModel(econ_model_scenario[0], econ_model_scenario[1], [])
os.makedirs(targetdir)

effectset.make_pval_file(targetdir, pvals)
standard.produce(targetdir, weatherbundle, economicmodel, get_model, pvals, do_farmers=True)
