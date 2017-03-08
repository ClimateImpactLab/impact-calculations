import sys
from netCDF4 import Dataset
from ..adaptation import csvvfile

csvvpath = sys.argv[1]

knowncovars = ['logpopop', 'loggdppc', '1', 'hotdd_agg', 'coldd_agg']

helps = set([])

try:
    # Read the CSVV
    data = csvvfile.read(csvvpath)

    # Read the climate data
    rootgrp = Dataset(filepath, 'r', format='NETCDF4')
    varinfo = {var: rootgrp.variables[var].units for var in rootgrp.variables.keys()}

    for predname in data['prednames']:
        if predname not in varinfo:
            print "ERROR: Predictor %s is not a known weather variable." % predname
            helps.add("varinfo")
            continue

        if predname not in data['variables']:
            print "ERROR: Predictor %s is not defined in the header information."

        if data['variables'][predname]['units'] != varinfo[predname]:
            print "ERROR: Units mismatch for predictor %s: %s <> %s." % (predname, data['variables'][predname]['units'], varinfo[predname])
            continue

    for covarname in data['covarnames']:
        if covarname not in (varinfo + knowncovars):
            print "ERROR: Covariate %s is not a known weather variable." % covarname
            helps.add("varinfo")
            continue

        if covarname not in data['variables']:
            print "ERROR: Covariate %s is not defined in the header information."

        if data['variables'][covarname]['units'] != varinfo[covarname]:
            print "ERROR: Units mismatch for covariate %s: %s <> %s." % (covarname, data['variables'][covarname]['units'], varinfo[covarname])
            continue

    assert len(data['gamma']) == len(data['prednames']), "ERROR: Must have as many gamma values as predictors."
    assert len(data['covarnames']) == len(data['prednames']), "ERROR: Must have as many covariates as predictors."
    assert data['gammavcv'].shape == (len(data['gamma']), len(data['gamma'])), "ERROR: Gamma VCV must describe all gammas."
