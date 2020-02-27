"""
List all known weather datasets
"""

import os, importlib, yaml
from generate import loadmodels, weather
from interpret import configs
from climate.discover import standard_variable
from impactlab_tools.utils import files

config = configs.standardize(files.get_allargv_config())
config['show-source'] = True

mod = importlib.import_module("interpret.container")
mod.preload()

timerate = config.get('timerate', 'day')
discoverers = []
for variable in config['climate']:
    print(variable)
    discoverer = standard_variable(variable, timerate, **config)
    discoverers.append(discoverer)

for clim_scenario, clim_model, weatherbundle in weather.iterate_bundles(*discoverers, **config):
    print((clim_scenario, clim_model))
