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
import cProfile, pstats, StringIO

do_profile = False

config = files.get_allargv_config()

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
    weatherbundle = weather.HistoricalWeatherBundle.make_historical(weatherbundle, pvals['histclim'].get_seed())
    pvals.lock()

print "Loading economics..."
economicmodel = econmodel.get_economicmodel(econ_scenario, econ_model)

print "Loading estimates..."
csvvpath = config['csvvpath']
basename = os.path.basename(csvvpath)[:-5]

csvv = csvvfile.read(files.configpath(csvvpath))
csvvfile.collapse_bang(csvv, pvals[basename].get_seed())

if 'csvvsubset' in config:
    indices = interpret.read_range(config['csvvsubset'])
    csvv = csvvfile.subset(csvv, indices)

suffix, farmer = farming.interpret(config)

print "Loading weights..."
get_weight = weights.interpret(config)

if not os.path.exists(targetdir):
    os.makedirs(targetdir)

print "Loading calculation..."

if do_profile:
    config['mode'] = 'profile'

    pr = cProfile.Profile()
    pr.enable()

if 'module' in config:
    module = "impacts." + config['module']
    calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(csvv, module, weatherbundle, economicmodel, pvals[basename], farmer=farmer)

elif 'specification' in config:
    from interpret import specification
    specconf = config['specification']
    calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(csvv, 'interpret.specification', weatherbundle, economicmodel, pvals[basename], specconf=specconf)

else:
    print "ERROR: Unknown model specification method."
    exit()
    
effectset.generate(targetdir, basename + suffix, weatherbundle, calculation, "Singly produced result.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, filter_region=filter_region)

if do_profile:
    pr.disable()

    s = StringIO.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(.5)
    #ps.print_callers('__getitem__')
    print s.getvalue()
    
    exit()

aggregate.make_levels(targetdir, basename + suffix + '.nc4', aggregate.fullfile(basename, aggregate.levels_suffix, config), get_weight)
aggregate.make_aggregates(targetdir, basename + suffix + '.nc4', aggregate.fullfile(basename, aggregate.suffix, config), get_weight)


