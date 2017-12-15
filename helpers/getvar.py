"""
Call as:
$ python -m helpers.getvar ...allmodels.yml <variable> <region>

The configuration file provides the bundle iterator (top-level climate discovered variables).
"""

import sys, importlib, yaml, os
from impactlab_tools.utils import files
from generate import loadmodels

config = files.get_allargv_config()

## Note: Copied from generate.py
if config['module'][-4:] == '.yml':
    mod = importlib.import_module("interpret.container")
    with open(config['module'], 'r') as fp:
        config.update(yaml.load(fp))
    shortmodule = os.path.basename(config['module'])[:-4]
else:
    mod = importlib.import_module("impacts." + config['module'] + ".allmodels")
    shortmodule = config['module']

variable = sys.argv[1]
region = 'IND.33.542.2153'

clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel = loadmodels.single(mod.get_bundle_iterator(config))
