"""
Performs a prediction for a single model and a single adaptation assumption and aggregates.
"""

import weather
from impactlab_tools.utils import files

config = files.get_allargv_config()

module = "impacts." + config['module']
CLIMATEMAPPING = config['CLIMATEMAPPING']

targetdir = config['targetdir']
pvals = pvalses.interpret(config['pvals'])
clim_scenario = config['rcp']
clim_model = config['gcm']
econ_scenario = config['ssp']
econ_model = config['iam']

weatherbundle = weather.get_weatherbundle(clim_scenario, clim_model)
economicmodel = econmodel.get_economicmodel(econ_scenario, econ_model)

csvvpath = config['csvvpath']
basename = os.path.basename(csvvpath)[:-5]

csvv = csvvfile.read(csvvpath)

suffix, farmer, weatherbundle = adaptation.interpret(config['adaptation'], weatherbundle)

calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(csvv, module, weatherbundle, economicmodel, pvals[basename])

effectset.generate(targetdir, basename + suffix, weatherbundle, calculation, None, "Singly produced result.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, farmer=farmer)

## CHANGES: Collapse the two suffixes, drop None argument

get_weight = datastore.interpret(config['weights'])

aggregate.make_levels(targetdir, basename + suffix + '.nc4', get_weight)
aggregate.make_aggregates(targetdir, basename + suffix + '.nc4', get_weight)

