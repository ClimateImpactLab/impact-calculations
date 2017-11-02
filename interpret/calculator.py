import yaml
from openest.generate import stdlib, arguments
from generate import caller

def create_calculation(postconf, models):
    if isinstance(postconf, str):
        with open(postconf, 'r') as fp:
            postconf = yaml.load(fp)

    calculation = create_calcstep(postconf[0].keys()[0], postconf[0].values()[0], models, None)
    return create_postspecification(postconf[1:], models, calculation)

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

    arglist = []
    kwargs = {}
    for argtype in cls.describe()['arguments']:
        if argtype == arguments.calculation:
            arglist.append(subcalc)
        elif argtype in [arguments.model, arguments.curvegen, arguments.curve_or_curvegen]:
            arglist.append(models['default'])
        elif argtype.name in ['input_unit', 'output_unit'] and argtype.name in kwargs:
            arglist.append(kwargs[argtype.name])
        else:
            try:
                arg = get_argument(argtype.name)
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
                            raise ValueError("Could not find required argument %s" % argtype.name)
                else:
                    if argtype.name in extras:
                        arglist.append(extras[argtype.name])
                    else:
                        raise ValueError("Could not find required argument %s" % argtype.name)

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

