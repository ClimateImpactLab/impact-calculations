"""
Performs a prediction for a single model and a single adaptation assumption and aggregates.
"""

import weather, pvalses
from impactlab_tools.utils import files
from climate import discover
from datastore import weights
from adaptation import farming
from helpers import interpret

config = files.get_allargv_config()

module = "impacts." + config['module']

targetdir = config['targetdir']
pvals = pvalses.interpret(config) # pvals
clim_scenario = config['rcp']
clim_model = config['gcm']
econ_scenario = config['ssp']
econ_model = config['iam']

variables = [discover.standard_variable(name, 'day') for name in config['climate']]

clim_scenario, clim_model, weatherbundle = weather.get_weatherbundle(clim_scenario, clim_model, variables)
economicmodel = econmodel.get_economicmodel(econ_scenario, econ_model)

csvvpath = config['csvvpath']
basename = os.path.basename(csvvpath)[:-5]

get_weight = weights.interpret(config)

csvv = csvvfile.read(csvvpath)
csvvfile.collapse_bang(csvv, pvals[basename].get_seed())

if 'csvvsubset' in config:
    indices = interpret.read_range(config['csvvsubset'])
    csvv = csvvfile.subset(csvv, indices)

suffix, farmer = farming.interpret(config)

if 'historical' in config and config['historical']:
    weatherbundle = weather.RepeatedHistoricalWeatherBundle.make_historical(weatherbundle, pvals['histclim'].get_seed())
    pvals.lock()

calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(csvv, module, weatherbundle, economicmodel, pvals[basename])

effectset.generate(targetdir, basename + suffix, weatherbundle, calculation, "Singly produced result.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, farmer=farmer)

aggregate.make_levels(targetdir, basename + suffix + '.nc4', get_weight)
aggregate.make_aggregates(targetdir, basename + suffix + '.nc4', get_weight)

