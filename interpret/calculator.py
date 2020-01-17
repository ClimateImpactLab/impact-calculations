import yaml, copy, sys, traceback
from openest.generate import stdlib, arguments
from generate import caller
import curves

def prepare_argument(name, argument, models, argtype, extras={}):
    """Translate a configuration option `argument` into an object of type `argtype`."""
    if argtype in [arguments.model, arguments.curvegen, arguments.curve_or_curvegen]:
        assert argument in models, "Unknonwn model %s" % argument
        return models[argument]

    if argtype == arguments.calculationss:
        assert isinstance(argument, list)
        return [create_calcstep(argii.keys()[0], argii.values()[0], models, None, extras=extras) for argii in argument]

    if argtype.isa(arguments.calculation):
        subcalc = extras.get('subcalc', None)
        return create_calcstep(argument.keys()[0], argument.values()[0], models, subcalc, extras=extras)
    
    return argument

last_tryprepare_error = None
def tryprepare_argument(name, argument, models, argtype, extras={}):
    """Attempt to interpret argument as an argtype and return it; if this fails, return None."""
    global last_tryprepare_error
    try:
        return prepare_argument(name, argument, models, argtype, extras=extras)
    except:
        last_tryprepare_error = traceback.format_exc() # don't save actual exception (gc problems)
        return None

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

def extract_units(argstr, savedargs):
    """Expect an argument of the form "[input units] -> [output units]. Save these to savedargs."""
    input_unit, output_unit = tuple(argstr.split(' -> '))
    savedargs['input_unit'] = input_unit
    savedargs['output_unit'] = output_unit

def get_unitsarg(name, argtype, get_argument, has_argument, savedargs, extras):
    """Try to get the given requested unit argument, handling all cases. Arguments must have come as dictionary."""
    if has_argument(argtype.name):
        return get_argument(argtype.name)
    if argtype.name in savedargs:
        return savedargs[argtype.name]
    if argtype.name in extras:
        return extras[argtype.name]
    if argtype.isa(arguments.input_unit) and argtype.name != 'indepunit':
        return get_unitsarg(name, argtype.rename('indepunit'), get_argument, has_argument, savedargs, extras)
    if argtype.isa(arguments.output_unit) and argtype.name != 'depenunit':
        return get_unitsarg(name, argtype.rename('depenunit'), get_argument, has_argument, savedargs, extras)
    raise ValueError("Could not find required units %s of %s" % (argtype.name, name))
    
def create_calcstep(name, args, models, subcalc, extras={}):
    if name == 'Rebase':
        if isinstance(args, dict):
            kwargs = args
        else:
            kwargs = {}
        return caller.standardize(subcalc, **kwargs)

    if name == 'PartialDerivative':
        assert isinstance(args, dict)
        assert 'covariate' in args and 'covarunit' in args
        return subcalc.partial_derivative(args['covariate'], args['covarunit'])
    
    cls = getattr(stdlib, name)

    if isinstance(args, list):
        remainingargs = copy.copy(args)
        get_argument = lambda name: remainingargs.pop(0)
        has_argument = lambda name: len(remainingargs) > 0
    else:
        get_argument = lambda name: args[name]
        has_argument = lambda name: name in args
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
        if argtype.isa(arguments.calculation):
            if subcalc is not None and subcalc not in arglist:
                arglist.append(subcalc)
            else:
                # other calculation might need this one (e.g., AuxillaryResult)
                subextras = copy.copy(extras)
                subextras['subcalc'] = subcalc
                arglist.append(prepare_argument(argtype.name, get_argument(argtype.name), models, argtype, extras=subextras))
        elif argtype == arguments.calculationss and isinstance(args, list):
            calculations = []
            while len(remainingargs) > 0:
                calcarg = tryprepare_argument(argtype.name, remainingargs[0], models, arguments.calculation, extras=extras)
                if calcarg is None:
                    break # end of the calculations list
                calculations.append(calcarg)
                remainingargs.pop(0)
            if len(calculations) == 0:
                print last_tryprepare_error
                raise ValueError("Cannot interpret any arguments as calculations!")
            arglist.append(calculations)
        elif argtype in [arguments.model, arguments.curvegen, arguments.curve_or_curvegen]:
            if 'default' in models:
                arglist.append(models['default'])
            else:
                arglist.append(prepare_argument(argtype.name, get_argument(argtype.name), models, argtype, extras=extras))
        elif argtype.name in ['input_unit', 'output_unit'] and argtype.name in savedargs:
            arglist.append(savedargs[argtype.name])
        else:
            if not has_argument(argtype.name):
                gotarg = False
                argconfig = None
                arg = None
            else:
                gotarg = True
                argconfig = get_argument(argtype.name)
                arg = tryprepare_argument(argtype.name, argconfig, models, argtype, extras=extras)
            if arg is not None:
                if argtype.name in ['input_unit', 'output_unit'] and ' -> ' in arg:
                    extract_units(arg, savedargs)
                    arglist.append(savedargs[argtype.name])
                    continue
                elif getattr(argtype, 'is_optional', False):
                    if isinstance(arg, dict) and len(arg) == 1 and argtype.name in arg:
                        kwargs[argtype.name] = arg[argtype.name]
                    else:
                        kwargs[argtype.name] = arg
                else:
                    arglist.append(arg)
            else:
                if getattr(argtype, 'is_optional', False):
                    if isinstance(args, list) and gotarg:
                        args.insert(0, argconfig)
                    continue
                if isinstance(args, dict) and (argtype.isa(arguments.input_unit) or argtype.isa(arguments.output_unit)):
                    if has_argument('units'):
                        arg = get_argument('units')
                        extract_units(arg, savedargs)
                    arglist.append(get_unitsarg(name, argtype, get_argument, has_argument, savedargs, extras))
                else:
                    if argtype.name in extras:
                        arglist.append(extras[argtype.name])
                        if isinstance(args, list) and gotarg:
                            args.insert(0, argconfig)
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
