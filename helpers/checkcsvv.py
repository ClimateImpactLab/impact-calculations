import sys, os
from netCDF4 import Dataset
from adaptation import csvvfile
from climate import discover

csvvpath = sys.argv[1]

knownpreds = {'belowzero': None}
knowncovars = {'logpopop': 'log ppl/km^2', 'loggdppc': 'log USD2000', '1': '', 'hotdd_agg': 'C day', 'coldd_agg': 'C day'}

helps = set([])

# Read the CSVV
try:
    data = csvvfile.read(csvvpath)
except Exception as e:
    print "ERROR: Cannot read CSVV file."
    print e
    exit()

for predname in set(data['prednames']):
    if predname not in knownpreds:
        try:
            discoverer = discover.standard_variable(predname, 'day')
        except:
            print "ERROR: Predictor %s is not a known weather variable." % predname
            continue

        scenario, model, pastreader, futurereader = discoverer.next()
        unit = pastreader.units
    else:
        unit = knownpreds[predname]

    if predname not in data['variables']:
        print "ERROR: Predictor %s is not defined in the header information." % predname
        continue

    if unit is not None and data['variables'][predname]['unit'] != unit:
        print "ERROR: Units mismatch for predictor %s: %s <> %s." % (predname, data['variables'][predname]['unit'], pastreader.units)
        continue

for covarname in data['covarnames']:
    if covarname not in knowncovars:
        try:
            discoverer = discover.standard_variable(predname, 'day')
        except:
            try:
                discoverer = discover.standard_variable(predname, 'year')
            except:
                print "ERROR: Covariate %s is not a known weather variable." % covarname
                continue
        scenario, model, pastreader, futurereader = discoverer.next()
        unit = pastreader.units
    else:
        unit = knowncovars[covarname]        

    if covarname == '1':
        continue

    if covarname not in data['variables']:
        print "ERROR: Covariate %s is not defined in the header information." % covarname
        continue

    if data['variables'][covarname]['unit'] != unit:
        print "ERROR: Units mismatch for covariate %s: %s <> %s." % (covarname, data['variables'][covarname]['unit'], unit)
        continue
            
assert len(data['gamma']) == len(data['prednames']), "ERROR: Must have as many gamma values as predictors."
assert len(data['covarnames']) == len(data['prednames']), "ERROR: Must have as many covariates as predictors."
assert data['gammavcv'].shape == (len(data['gamma']), len(data['gamma'])), "ERROR: Gamma VCV must describe all gammas."
