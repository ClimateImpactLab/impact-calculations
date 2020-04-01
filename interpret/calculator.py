"""Interpret the calculations sequence in a configuration file.

Calculation objects have self-documented arguments, and these are used
to interpret the `calculations` dictionary in the spec. configuration
file. The `describe` function on a Calculation object returns a list
of `BaseArgument` objects, which are matched to information in the
configuration file.

Calculation objects are read in order, with any `subcalc`
Calculation argument of each Calculation applied to the previous
Calculation object. Other arguments are read from either the
subdirectory specific to that Calculation or from parent dictionaries
in the configuration file.

In the configuration file, arguments may be provided in either a list
or a dictionary. If provided as a list, they must be given in the same
order as the Calculation object's `describe` method. If provided a
dictionary, they must use the names referenced in the `describe`
method.

Specially handling is used for units, since units can be provided as a
single item in the configuration file (as `indepunits -> depenunit`,
but fed into two arguments in the creation of the Calculation object.
"""

import yaml, copy, sys, traceback
from openest.generate import stdlib, arguments
from generate import caller
from . import curves

def prepare_argument(name, argument, models, argtype, extras=None):
    """Translate a configuration option `argument` into an object of type `argtype`.

    Parameters
    ----------
    name : str
    argument : MutableMapping or List
    models : MutableMapping
        Mapping with str names and ``adaptation.curvegen.FarmerCurveGenerator``
        values.
    argtype : openest.generate.arguments_base.ArgumentType
    extra : MutableMapping or None, optional
        Might contain subcalculation information as the value under the
        "subcalc" key, along with additional keys/values to pass to 
        ``create_calcstep()``.

    Returns
    -------
    """
    if extras is None:
        extras = {}
    if argtype in [arguments.model, arguments.curvegen, arguments.curve_or_curvegen]:
        assert argument in models, "Unknonwn model %s" % argument
        return models[argument]

    if argtype == arguments.calculationss:
        assert isinstance(argument, list)
        return [create_calcstep(list(argii.keys())[0], list(argii.values())[0], models, None, extras=extras) for argii in argument]

    if argtype.isa(arguments.calculation):
        subcalc = extras.get('subcalc', None)
        return create_calcstep(list(argument.keys())[0], list(argument.values())[0], models, subcalc, extras=extras)
    
    return argument

last_tryprepare_error = None
def tryprepare_argument(name, argument, models, argtype, extras=None):
    """Attempt to interpret argument as an argtype and return it; if this fails, return None.

    All parameters are passed to ``prepare_argument()``.

    Parameters
    ----------
    name : str
    argument : MutableMapping or List
    models : MutableMapping
    argtype : openest.generate.arguments_base.ArgumentType
    extra : MutableMapping or None, optional

    Returns
    -------
    """
    if extras is None:
        extras = {}
    global last_tryprepare_error
    try:
        return prepare_argument(name, argument, models, argtype, extras=extras)
    except Exception as ex:
        print("Exception but returning:")
        print(ex)
        last_tryprepare_error = traceback.format_exc() # don't save actual exception (gc problems)
        return None

def create_calculation(postconf, models, extras=None):
    """Creates initial calculation step based on some fancy specifications

    Parameters
    ----------
    postconf : str or Sequence
        Path to yaml file or sequence of Calculation configurations.
    models : MutableMapping
        Mapping with str names and ``adaptation.curvegen.FarmerCurveGenerator``
        values.
    extra : MutableMapping or None, optional
        Passed to ``create_calcstep()`` and then ``create_postspecification``.

    Returns
    -------
    """
    if extras is None:
        extras = {}
    if isinstance(postconf, str):
        with open(postconf, 'r') as fp:
            postconf = yaml.load(fp)

    calculation = create_calcstep(list(postconf[0].keys())[0], list(postconf[0].values())[0], models, None, extras=extras)
    return create_postspecification(postconf[1:], models, calculation, extras=extras)

def create_postspecification(postconf, models, calculation, extras=None):
    """Loop through non-initial calculation step(s) based on more fancy specs

    Parameters
    ----------
    postconf : str or Sequence
        Path to yaml file or sequence of Calculation configurations.
    models : MutableMapping
        Mapping with str names and ``adaptation.curvegen.FarmerCurveGenerator``
        values.
    extra : MutableMapping or None, optional
        Passed along to ``create_calcstep()``.

    Returns
    -------
    """
    if extras is None:
        extras = {}
    if isinstance(postconf, str):
        with open(postconf, 'r') as fp:
            postconf = yaml.load(fp)
    
    for calcstep in postconf:
        if isinstance(calcstep, str):
            calculation = create_calcstep(calcstep, {}, models, calculation, extras=extras)
        else:
            calculation = create_calcstep(list(calcstep.keys())[0], list(calcstep.values())[0], models, calculation, extras=extras)

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

def get_namedarg(args, name):
    """Return the requested argument, handling aliases."""
    if name in args:
        return args[name]

    if name == 'unshift':
        return not args['dropprev']
    if name == 'dropprev':
        return not args['unshift']

    raise KeyError(name)

def create_calcstep(name, args, models, subcalc, extras=None):
    if extras is None:
        extras = {}
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
        get_argument = lambda name: get_namedarg(args, name)
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
                print(last_tryprepare_error)
                raise ValueError("Cannot interpret any arguments as calculations!")
            arglist.append(calculations)
        elif argtype in [arguments.model, arguments.curvegen, arguments.curve_or_curvegen]:
            if 'default' in models:
                arglist.append(models['default'])
            else:
                arglist.append(prepare_argument(argtype.name, get_argument(argtype.name), models, argtype, extras=extras))
        elif argtype.name in ['input_unit', 'output_unit'] and argtype.name in savedargs:
            arglist.append(savedargs[argtype.name])
        elif argtype.types == [list] and isinstance(args, list) and cls.describe()['arguments'][-1] == argtype: # Allow a trailing list to capture remaining arguments
            arglist.append(remainingargs)
            remainingargs = []
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
                        kwargs[argtype.name] = get_namedarg(arg, argtype.name)
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
    except Exception as ex:
        print("Exception but printing other stuff:")
        print(ex)
        t, v, tb = sys.exc_info()
        print(cls)
        print(arglist)
        raise t(v).with_traceback(tb)

def sample_sequence(calculation, region):
    application = calculation.apply(region)
    for year, ds in weatherbundle.yearbundles():
        print("%d:" % year)
        subds = ds.sel(region=region)
        for yearresult in application.push(subds):
            print("    ", yearresult)
