"""
Performs a prediction for a single model and a single adaptation assumption and aggregates.
"""

print "Initializing..."

import os
from impactlab_tools.utils import files
from climate import discover
from datastore import weights
from adaptation import farming, econmodel, csvvfile
from helpers import interpret
import weather, pvalses, caller, effectset, aggregate

config = files.get_allargv_config()

module = "impacts." + config['module']

targetdir = config['targetdir']
pvals = pvalses.interpret(config) # pvals
clim_scenario = config['rcp']
clim_model = config['gcm']
econ_scenario = config['ssp']
econ_model = config['iam']

print "Loading weather..."
variable_generators = [discover.standard_variable(name, 'day') for name in config['climate']]
weatherbundle = weather.get_weatherbundle(clim_scenario, clim_model, variable_generators)

filter_region = config.get('filter-region', None)

if 'historical' in config and config['historical']:
    weatherbundle = weather.HistoricalWeatherBundle.make_historical(weatherbundle, pvals['histclim'].get_seed('yearorder'))
    pvals.lock()

print "Loading economics..."
economicmodel = econmodel.get_economicmodel(econ_scenario, econ_model)

print "Loading estimates..."
csvvpath = config['csvvpath']
basename = os.path.basename(csvvpath)[:-5]

csvv = csvvfile.read(files.configpath(csvvpath))
csvvfile.collapse_bang(csvv, pvals[basename].get_seed('csvv'))

if 'csvvsubset' in config:
    indices = interpret.read_range(config['csvvsubset'])
    csvv = csvvfile.subset(csvv, indices)

suffix, farmer = farming.interpret(config)

print "Loading weights..."
halfweight = weights.interpret(config)
halfweight_args = weights.get_weight_args(config)

print "Loading calculation..."
calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(csvv, module, weatherbundle, economicmodel, pvals[basename], farmer=farmer)

if not os.path.exists(targetdir):
    os.makedirs(targetdir, 0775)

effectset.generate(targetdir, basename + suffix, weatherbundle, calculation, "Singly produced result.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, filter_region=filter_region)

filename = basename + suffix + '.nc4'
aggregate.make_levels(targetdir, filename, aggregate.fullfile(filename, aggregate.levels_suffix, config), halfweight, halfweight_args)
aggregate.make_aggregates(targetdir, filename, aggregate.fullfile(filename, aggregate.suffix, config), halfweight, halfweight_args)

