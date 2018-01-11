"""
Call as:
$ python -m helpers.getvar ...allmodels.yml <variable>
Or as:
$ python -m helpers.getvar <variable> <timerate>

The configuration file provides the bundle iterator (top-level climate discovered variables).
"""

import sys, importlib, yaml, os
import numpy as np
from impactlab_tools.utils import files
from climate import discover
from generate import weather, loadmodels
from interpret import variables

region = "IND.33.542.2153"
varname = ' '.join(sys.argv[2:])

found_bundle = None
if sys.argv[1][-4:] != '.yml':
    # Use <variable> <timerate> syntax
    bundle_iterator = weather.iterate_bundles(discover.standard_variable(sys.argv[1], varname))

    transform = lambda ds: ds[varname]
    
    for scenario, model, bundle in bundle_iterator:
        if scenario == 'rcp85' and model == 'CCSM4':
            found_bundle = bundle
            break
else:
    # Use <config> <variable> syntax
    config = files.get_allargv_config()

    transform = variables.interpret_ds_transform(varname, config)
    
    ## Note: Copied from generate.py
    if config['module'][-4:] == '.yml':
        mod = importlib.import_module("interpret.container")
        with open(config['module'], 'r') as fp:
            config.update(yaml.load(fp))
        shortmodule = os.path.basename(config['module'])[:-4]
    else:
        mod = importlib.import_module("impacts." + config['module'] + ".allmodels")
        shortmodule = config['module']

    clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel = loadmodels.single(mod.get_bundle_iterator(config))
    found_bundle = weatherbundle

if found_bundle is None:
    print "Cannot find valid weather data."
    exit(-1)
    
rr = found_bundle.regions.index(region)
for year, ds in found_bundle.yearbundles():
    print transform(ds)
    exit(0)
