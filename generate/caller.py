import importlib
from datastore import library
import server, effectset
from adaptation import csvvfile
from openest.generate.stdlib import *

get_data = library.get_data
get_model = effectset.get_model_server

callinfo = None

def get_model_by_gcpid(gcpid):
    wks, header, ids = server.get_model_info()
    rowvalues = wks.row_values(ids.index(gcpid) + 1)
    return get_model(rowvalues[header.index('DMAS ID')])

def standardize(calculation):
    if calculation.unitses[0] in ['deaths/person/year'] or calculation.unitses[0][0:7] == 'minutes':
        return SpanInstabase(calculation, 2001, 2010, func=lambda x, y: x - y)
    else:
        assert False, "Unexpected units " + calculation.unitses[0]

def call_prepare(module, weatherbundle, economicmodel, pvals, getmodel=get_model, getdata=get_data):
    if module[0:15] == 'impacts.health.':
        gcpid = module[15:]
    else:
        gcpid = None

    mod = importlib.import_module(module)

    if 'prepare_raw' in dir(mod):
        calculation, dependencies = mod.prepare_raw(pvals, getmodel, getdata)
        return standardize(calculation), dependencies

    if 'prepare_interp_raw' in dir(mod):
        calculation, dependencies, curve, baseline_get_predictors = mod.prepare_interp_raw(weatherbundle, economicmodel, pvals, getdata)
        return standardize(calculation), dependencies, curve, baseline_get_predictors

    if 'prepare_raw_spr' in dir(mod):
        wks, header, ids = server.get_model_info()
        rowvalues = wks.row_values(ids.index(gcpid) + 1)
        spreadrow = {header[ii]: rowvalues[ii] for ii in range(min(len(header), len(rowvalues)))}
        calculation, dependencies = mod.prepare_raw_spr(spreadrow, pvals, getmodel, getdata)
        return standardize(calculation), dependencies

    raise ValueError("Could not find known prepare form.")

def call_prepare_interp(filepath, module, weatherbundle, economicmodel, pvals, farmer='full'):
    mod = importlib.import_module(module)
    csvv = csvvfile.read(filepath)

    if 'prepare_interp_raw' in dir(mod):
        calculation, dependencies, baseline_get_predictors = mod.prepare_interp_raw(csvv, weatherbundle, economicmodel, pvals, farmer)
        return standardize(calculation), dependencies, baseline_get_predictors

    raise ValueError("Could not find known prepare form.")
