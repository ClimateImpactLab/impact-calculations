import sys, os
from netCDF4 import Dataset
from adaptation import csvvfile

csvvpath = sys.argv[1]

knowncovars = {'logpopop': 'log ppl/km^2', 'loggdppc': 'log USD2000', '1': '', 'hotdd_agg': 'C day', 'coldd_agg': 'C day'}

helps = set([])

# Read the CSVV
try:
    data = csvvfile.read(csvvpath)
except Exception as e:
    print "ERROR: Cannot read CSVV file."
    print e
    exit()

# Read the climate data
varinfo = {}
for climpath in sys.argv[2:]:
    if os.path.isdir(climpath):
        climpath = os.path.join(climpath, filter(lambda name: os.path.splitext(name)[1] in ['.nc', '.nc4'], os.listdir(climpath))[0])
    rootgrp = Dataset(climpath, 'r', format='NETCDF4')

    diminfo = {}
    for dim in rootgrp.variables.keys():        
        if len(rootgrp.variables[dim].shape) == 1:
            diminfo[dim] = rootgrp.variables[dim][:]

    for var in rootgrp.variables.keys():
        if len(rootgrp.variables[var].shape) > 1:
            if len(rootgrp.variables[var].shape) == 3:
                if min(rootgrp.variables[var].shape) == rootgrp.variables[var].shape[1]:
                    # Find the right dim
                    for dim in diminfo:
                        if len(diminfo[dim]) == rootgrp.variables[var].shape[1]:
                            for ii in range(len(diminfo[dim])):
                                varinfo[var + '-' + str(diminfo[dim][ii])] = rootgrp.variables[var].units
            else:
                varinfo[var] = rootgrp.variables[var].units

print varinfo

for predname in data['prednames']:
    if predname not in varinfo:
        print "ERROR: Predictor %s is not a known weather variable." % predname
        helps.add("varinfo")
        continue

    if predname not in data['variables']:
        print "ERROR: Predictor %s is not defined in the header information." % predname

    if data['variables'][predname]['unit'] != varinfo[predname]:
        print "ERROR: Units mismatch for predictor %s: %s <> %s." % (predname, data['variables'][predname]['unit'], varinfo[predname])
        continue

for covarname in data['covarnames']:
    if covarname not in (varinfo.keys() + knowncovars.keys()):
        print "ERROR: Covariate %s is not a known weather variable." % covarname
        helps.add("varinfo")
        continue

    if covarname == '1':
        continue

    if covarname not in data['variables']:
        print "ERROR: Covariate %s is not defined in the header information." % covarname

    if covarname in varinfo:
        if data['variables'][covarname]['unit'] != varinfo[covarname]:
            print "ERROR: Units mismatch for covariate %s: %s <> %s." % (covarname, data['variables'][covarname]['unit'], varinfo[covarname])
            continue
    elif covarname in knowncovars:
        if data['variables'][covarname]['unit'] != knowncovars[covarname]:
            print "ERROR: Units mismatch for covariate %s: %s <> %s." % (covarname, data['variables'][covarname]['unit'], knowncovars[covarname])
            continue
            
assert len(data['gamma']) == len(data['prednames']), "ERROR: Must have as many gamma values as predictors."
assert len(data['covarnames']) == len(data['prednames']), "ERROR: Must have as many covariates as predictors."
assert data['gammavcv'].shape == (len(data['gamma']), len(data['gamma'])), "ERROR: Gamma VCV must describe all gammas."

if 'varinfo' in helps:
    print "Available climate variables:"
    for predname in varinfo:
        print "  %s [%s]" % (predname, varinfo[predname])
