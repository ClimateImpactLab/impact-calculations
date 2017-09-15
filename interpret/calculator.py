import yaml
from openest.generate import stdlib
from generate import caller

def create_calculation(postconf, models):
    if isinstance(postconf, str):
        with open(postconf, 'r') as fp:
            postconf = yaml.load(fp)

    calculation = create_calcstep(postconf[0].keys()[0], postconf[0].values()[0], models, None)
    return create_postspecification(postconf[1:], models, calculation)

def create_postspecification(postconf, models, calculation):
    if isinstance(postconf, str):
        with open(postconf, 'r') as fp:
            postconf = yaml.load(fp)
    
    for calcstep in postconf:
        if isinstance(calcstep, str):
            calculation = create_calcstep(calcstep, {}, models, calculation)
        else:
            calculation = create_calcstep(calcstep.keys()[0], calcstep.values()[0], models, calculation)

    return calculation

def create_calcstep(name, args, models, subcalc):
    if name == 'Rebase':
        return caller.standardize(subcalc)

    cls = getattr(stdlib, name)

    if isinstance(args, list):
        generator = iter(args)
        get_argument = lambda name: generator.next()
    else:
        get_argument = lambda name: args[name]

    arglist = []
    for argtype in cls.describe()['arguments']:
        if argtype == arguments.calculation:
            arglist.append(subcalc)
        elif argtype in [arguments.model, arguments.curvegen, arguments.curve_or_curvegen]:
            arglist.append(models['default'])
        else:
            arglist.append(get_argument(argtype.name))

    return cls(*tuple(arglist))

def sample_sequence(calculation, region):
    application = calculation.apply(region)
    for year, ds in weatherbundle.yearbundles():
        print "%d:" % year
        subds = ds.sel(region=region)
        for yearresult in application.push(subds):
            print "    ", yearresult

