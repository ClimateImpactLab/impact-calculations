import yaml, copy, sys
from openest.generate import stdlib, arguments
from generate import caller
import curves

def prepare_argument(name, argument, models, argtype, extras={}):
    if argtype in [arguments.model, arguments.curvegen, arguments.curve_or_curvegen]:
        assert argument in models, "Unknonwn model %s" % argument
        return models[argument]

    if argtype == arguments.calculationss:
        assert isinstance(argument, list)
        return [create_calcstep(argii.keys()[0], argii.values()[0], models, None, extras=extras) for argii in argument]

    if argtype == arguments.calculation:
        return create_calcstep(argument.keys()[0], argument.values()[0], models, None, extras=extras)
    
    return argument

def create_calculation(postconf, models, extras={}):
    if isinstance(postconf, str):
        with open(postconf, 'r') as fp:
            postconf = yaml.load(fp)

    calculation = create_calcstep(postconf[0].keys()[0], postconf[0].values()[0], models, None, extras=extras)
    return create_postspecification(postconf[1:], models, calculation, extras=extras)

def create_postspecification(postconf, models, calculation, extras={}):
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
    if name == 'Rebase':
        if isinstance(args, dict):
            kwargs = args
        else:
            kwargs = {}
        return caller.standardize(subcalc, **kwargs)

    cls = getattr(stdlib, name)

    if isinstance(args, list):
        generator = iter(args)
        get_argument = lambda name: generator.next()
    else:
        get_argument = lambda name: args[name]
        if 'model' in args:
            # Set this up as the default model
            models = copy.copy(models)
            argmodel, argextras = curves.interpret(args['model'], models, extras)
            models['default'] = argmodel
            extras = copy.copy(extras)
            extras.update(argextras)
            args = copy.copy(args)
            del args['model']
            return create_calcstep(name, args, models, subcalc, extras)
        
    arglist = []
    kwargs = {}
    savedargs = {}
    for argtype in cls.describe()['arguments']:
        if argtype == arguments.calculation:
            if subcalc is not None:
                arglist.append(subcalc)
            else:
                arglist.append(prepare_argument(argtype.name, get_argument(argtype.name), models, argtype, extras=extras))
        elif argtype == arguments.calculationss and cls.describe()['arguments'][-1] == argtype and isinstance(args, list):
            # Special case for list of subcalcs
            arglist.append(prepare_argument(argtype.name, list(generator), models, argtype, extras=extras))
        elif argtype in [arguments.model, arguments.curvegen, arguments.curve_or_curvegen]:
            if 'default' in models:
                arglist.append(models['default'])
            else:
                arglist.append(prepare_argument(argtype.name, get_argument(argtype.name), models, argtype, extras=extras))
        elif argtype.name in ['input_unit', 'output_unit'] and argtype.name in savedargs:
            arglist.append(savedargs[argtype.name])
        else:
            try:
                arg = prepare_argument(argtype.name, get_argument(argtype.name), models, argtype, extras=extras)
                if argtype.name in ['input_unit', 'output_unit'] and ' -> ' in arg:
                    input_unit, output_unit = tuple(arg.split(' -> '))
                    savedargs['input_unit'] = input_unit
                    savedargs['output_unit'] = output_unit
                    arglist.append(savedargs[argtype.name])
                    continue
                elif getattr(argtype, 'is_optional', False):
                    if isinstance(arg, dict) and len(arg) == 1 and argtype.name in arg:
                        kwargs[argtype.name] = arg[argtype.name]
                    else:
                        kwargs[argtype.name] = arg
                else:
                    arglist.append(arg)
            except:
                if getattr(argtype, 'is_optional', False):
                    continue
                if argtype.name in ['input_unit', 'output_unit']:
                    try:
                        arg = get_argument('units')
                        input_unit, output_unit = typle(arg.split(' -> '))
                        savedargs['input_unit'] = input_unit
                        savedargs['output_unit'] = output_unit
                        arglist.append(savedargs[argtype.name])
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
        return cls(*tuple(arglist), **kwargs)
    except:
        t, v, tb = sys.exc_info()
        print cls
        print arglist
        raise t, v, tb

def sample_sequence(calculation, region):
    application = calculation.apply(region)
    for year, ds in weatherbundle.yearbundles():
        print "%d:" % year
        subds = ds.sel(region=region)
        for yearresult in application.push(subds):
            print "    ", yearresult
