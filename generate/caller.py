"""
Within the caller functions, mod is one of the calculation definition
modules contained in impacts/. So, for example, the main MLE results
for mortality are generated by
impacts/mortality/mle_cubic_spline.py. That's the module. The
calculation is brought into allmodels with the line
`caller.call_prepare_interp(filepath,
'impacts.mortality.mle_cubic_spline', weatherbundle, economicmodel,
pvals[basename])` (and that's how you know that's which module it is).
"""

import importlib
from datastore import library
from . import server, effectset
from adaptation import csvvfile
from openest.generate.stdlib import *

get_data = library.get_data
get_model = effectset.get_model_server

callinfo = None

def get_model_by_gcpid(gcpid):
    wks, header, ids = server.get_model_info()
    rowvalues = wks.row_values(ids.index(gcpid) + 1)
    return get_model(rowvalues[header.index('DMAS ID')])

def standardize(calculation, **kwargs):
    unit = calculation.unitses[0]
    return SpanInstabase(calculation, 2001, 2010, func=lambda x, y: x - y, units=unit, **kwargs)

def call_prepare(module, weatherbundle, economicmodel, pvals, getmodel=get_model, standard=True, getdata=get_data):
    economicmodel.reset()

    if module[0:15] == 'impacts.health.':
        gcpid = module[15:]
    else:
        gcpid = None

    if not standard:
        standardfunc = lambda x: x # Just pass through
    else:
        standardfunc = standardize

    mod = importlib.import_module(module)

    if 'prepare_raw' in dir(mod):
        calculation, dependencies = mod.prepare_raw(pvals, getmodel, getdata)
        return standardfunc(calculation), dependencies

    if 'prepare_interp_raw' in dir(mod):
        calculation, dependencies, curve, baseline_get_predictors = mod.prepare_interp_raw(weatherbundle, economicmodel, pvals, getdata)
        return standardfunc(calculation), dependencies, curve, baseline_get_predictors

    if 'prepare_raw_spr' in dir(mod):
        wks, header, ids = server.get_model_info()
        rowvalues = wks.row_values(ids.index(gcpid) + 1)
        spreadrow = {header[ii]: rowvalues[ii] for ii in range(min(len(header), len(rowvalues)))}
        calculation, dependencies = mod.prepare_raw_spr(spreadrow, pvals, getmodel, getdata)
        return standardfunc(calculation), dependencies

    raise ValueError("Could not find known prepare form.")

def call_prepare_interp(csvv, module, weatherbundle, economicmodel, pvals, farmer='full', standard=True, **kwargs):
    """Create the final calculation for a given model, according to the function that it exposes."""
    
    economicmodel.reset()

    mod = importlib.import_module(module)
    if isinstance(csvv, str):
        csvv = csvvfile.read(csvv)

    if not standard:
        standardfunc = lambda x: x # Just pass through
    else:
        standardfunc = standardize

    if 'prepare_raw' in dir(mod):
        calculation, dependencies = mod.prepare_raw(csvv, weatherbundle, economicmodel, pvals, **kwargs)
        return standardfunc(calculation), dependencies

    if 'prepare_interp_raw' in dir(mod):
        calculation, dependencies, baseline_get_predictors = mod.prepare_interp_raw(csvv, weatherbundle, economicmodel, pvals, farmer, **kwargs)
        return standardfunc(calculation), dependencies, baseline_get_predictors

    raise ValueError("Could not find known prepare form.")
