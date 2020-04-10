from interpret import specification, configs, calculator
from adaptation import csvvfile

def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full', specconf=None, config=None):
    # specconf here is the model containing 'specification' and 'calculation' keys
    if specconf is None:
        specconf = {}
    if config is None:
        config = {}
    assert 'calculation' in specconf
    assert 'specifications' in specconf

    if config.get('report-variance', False):
        csvv['gamma'] = np.zeros(len(csvv['gamma'])) # So no mistaken results
    else:
        csvvfile.collapse_bang(csvv, qvals.get_seed('csvv'))
        
    covariator = specification.create_covariator(specconf, weatherbundle, economicmodel, config, quiet=config.get('quiet', False))

    models = {}
    extras = dict(errorvar=csvvfile.get_errorvar(csvv))
    for key in specconf['specifications']:
        modelspecconf = configs.merge(specconf, specconf['specifications'][key])
        model = specification.create_curvegen(csvv, covariator, weatherbundle.regions,
                                              farmer=farmer, specconf=modelspecconf)
        modelextras = dict(output_unit=modelspecconf['depenunit'], units=modelspecconf['depenunit'],
                           curve_description=modelspecconf['description'])
        models[key] = model
        extras[key] = modelextras

    calculation = calculator.create_calculation(specconf['calculation'], models, extras=extras)

    if covariator is None:
        return calculation, [], lambda: {}
    else:
        return calculation, [], covariator.get_current
