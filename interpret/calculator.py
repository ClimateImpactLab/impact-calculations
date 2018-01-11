import yaml, copy
from openest.generate import stdlib, arguments
from generate import caller
from interpret import specification, configs
from adaptation import csvvfile

def prepare_argument(name, argument, models, argtype, extras={}):
    if argtype in [arguments.model, arguments.curvegen, arguments.curve_or_curvegen]:
        assert argument in models, "Unknonwn model %s" % argument
        return models[argument]

    if argtype == arguments.calculationss:
        assert isinstance(argument, list)
        return [create_calcstep(argii.keys()[0], argii.values()[0], models, None, extras=extras) for argii in argument]
    
    return argument

def create_calculation(postconf, models, extras={}):
    if isinstance(postconf, str):
        with open(postconf, 'r') as fp:
            postconf = yaml.load(fp)

    calculation = create_calcstep(postconf[0].keys()[0], postconf[0].values()[0], models, None, extras=extras)
    return create_postspecification(postconf[1:], models, calculation, extras=extras)

def create_postspecification(postconf, models, calculation, extras={}):
    print postconf
    if isinstance(postconf, str):
        with open(postconf, 'r') as fp:
            postconf = yaml.load(fp)
    
    for calcstep in postconf:
        if isinstance(calcstep, str):
            calculation = create_calcstep(calcstep, {}, models, calculation, extras=extras)
        else:
            calculation = create_calcstep(calcstep.keys()[0], calcstep.values()[0], models, calculation, extras=extras)

    return calculation

def create_calcstep(name, args, models, subcalc, extras={}):
    print name
    print args
    if name == 'Rebase':
        return caller.standardize(subcalc)

    cls = getattr(stdlib, name)

    if isinstance(args, list):
        generator = iter(args)
        get_argument = lambda name: generator.next()
    else:
        get_argument = lambda name: args[name]
        if 'model' in args:
            # Set this up as the default model
            models = copy.copy(models)
            models['default'] = models[args['model']]
            extras = copy.copy(extras)
            extras.update(extras[args['model']])
            args = copy.copy(args)
            del args['model']
            return create_calcstep(name, args, models, subcalc, extras)
        
    arglist = []
    kwargs = {}
    for argtype in cls.describe()['arguments']:
        if argtype == arguments.calculation:
            arglist.append(subcalc)
        elif argtype == arguments.calculationss and len(cls.describe()['arguments']) == 1 and isinstance(args, list):
            # Special case for list of subcalcs
            arglist.append(prepare_argument(argtype.name, args, models, argtype, extras=extras))
        elif argtype in [arguments.model, arguments.curvegen, arguments.curve_or_curvegen]:
            if 'default' in models:
                arglist.append(models['default'])
            else:
                arglist.append(prepare_argument(argtype.name, get_argument(argtype.name), models, argtype, extras=extras))
        elif argtype.name in ['input_unit', 'output_unit'] and argtype.name in kwargs:
            arglist.append(kwargs[argtype.name])
        else:
            try:
                arg = prepare_argument(argtype.name, get_argument(argtype.name), models, argtype, extras=extras)
                if argtype.name in ['input_unit', 'output_unit'] and ' -> ' in arg:
                    input_unit, output_unit = tuple(arg.split(' -> '))
                    kwargs['input_unit'] = input_unit
                    kwargs['output_unit'] = output_unit
                    arglist.append(kwargs[argtype.name])
                    continue
                else:
                    arglist.append(arg) # do it, and hope for the best
            except:
                if getattr(argtype, 'is_optional', False):
                    continue
                if argtype.name in ['input_unit', 'output_unit']:
                    try:
                        arg = get_argument('units')
                        input_unit, output_unit = typle(arg.split(' -> '))
                        kwargs['input_unit'] = input_unit
                        kwargs['output_unit'] = output_unit
                        arglist.append(kwargs[argtype.name])
                        continue
                    except:
                        if argtype.name in extras:
                            arglist.append(extras[argtype.name])
                        else:
                            raise ValueError("Could not find required argument %s of %s" % (argtype.name, name))
                else:
                    if argtype.name in extras:
                        arglist.append(extras[argtype.name])
                    else:
                        raise ValueError("Could not find required argument %s of %s" % (argtype.name, name))

    try:
        return cls(*tuple(arglist))
    except Exception as ex:
        print cls
        print arglist
        raise ex

def sample_sequence(calculation, region):
    application = calculation.apply(region)
    for year, ds in weatherbundle.yearbundles():
        print "%d:" % year
        subds = ds.sel(region=region)
        for yearresult in application.push(subds):
            print "    ", yearresult

def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full', specconf={}, config={}):
    # specconf here is the model containing 'specification' and 'calculation' keys
    assert 'calculation' in specconf
    assert 'specifications' in specconf
    
    csvvfile.collapse_bang(csvv, qvals.get_seed())
    covariator = specification.create_covariator(specconf, weatherbundle, economicmodel, config)

    models = {}
    extras = {}
    for key in specconf['specifications']:
        modelspecconf = configs.merge(specconf, specconf['specifications'][key])
        model = specification.create_curvegen(csvv, covariator, weatherbundle.regions,
                                              farmer=farmer, specconf=modelspecconf)
        modelextras = dict(output_unit=modelspecconf['depenunit'], units=modelspecconf['depenunit'],
                           curve_description=modelspecconf['description'])
        models[key] = model
        extras[key] = modelextras
    
    calculation = create_calculation(specconf['calculation'], models, extras=extras)

    if covariator is None:
        return calculation, [], lambda: {}
    else:
        return calculation, [], covariator.get_current
