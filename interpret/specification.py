"""Interpret the specifications sections of a configuration file.

As we define them, specifications are segments of the full
specification used by a sector's projection. For example, a projection
can consist of one polynomial specification applied to temperatures
over 20C and another for temperatures below 20C; or one polynomial
specification can be used for temperature and another for
precipitation.
"""

import re
from collections.abc import Mapping, Sequence
from adaptation import csvvfile, curvegen, curvegen_known, curvegen_arbitrary, covariates, constraints, parallel_covariates, parallel_econmodel
from generate import parallel_weather
from datastore import irvalues
from generate.weather import DailyWeatherBundle
from openest.generate import smart_curve
from openest.curves import ushape_numeric
from openest.curves.smart_linextrap import LinearExtrapolationCurve
from openest.generate.stdlib import *
from impactcommon.math import minpoly, minspline
from . import calculator, variables, configs

def user_failure(message):
    """Prints an 'ERROR' message and exits program"""
    print("ERROR: " + message)
    exit()

def user_assert(check, message):
    """If `check` False, send error message and exit program

    Parameters
    ----------
    check : bool
    message : str
    """
    if not check:
        user_failure(message)

def get_covariator(covar, args, weatherbundle, economicmodel, config=None, quiet=False, env=None):
    """Intreprets a single entry in the covariates dictionary.

    Parameters
    ----------
    covar : str or dict
        Covariate name, or ``{name: extra_args}``. If dict, value is pased in as 
        `args` recursively.
    args : list or None
        Additional postional arguments if `covar` values, if was dict.
    weatherbundle : generate.weather.DailyWeatherBundle
    economicmodel : adaptation.econmodel.SSPEconomicModel
    config : dict, optional
    quiet : bool
    env : dict of name => Covariator, optional
        This is an environment containing Covariator objects. Subclauses of `covar` may set variables within this environment.
        Typically, environments are not shared across config-file-level `covar` entries.

    Returns
    -------
    adaptation.covariates.Covariator
    """
    if config is None:
        config = {}
    if env is None:
        env = {}
    if isinstance(covar, Mapping):
        return get_covariator(list(covar.keys())[0], list(covar.values())[0], weatherbundle, economicmodel, config=config, quiet=quiet, env=env)
    elif covar in env:
        return env[covar]
    elif covar in ['loggdppc', 'logpopop', 'year']:
        return covariates.EconomicCovariator(economicmodel, 2015, config=configs.merge(config, 'econcovar'))
    elif covar in ['loggdppc.country', 'logpopop.country']:
        return covariates.EconomicCovariator(economicmodel, 2015, country_level=True, config=configs.merge(config, 'econcovar'))
    elif covar == 'incbin':
        return covariates.BinnedEconomicCovariator(economicmodel, 2015, args, config=configs.merge(config, 'econcovar'))
    elif covar == 'loggdppc-shifted':
        return covariates.ShiftedEconomicCovariator(economicmodel, 2015, config=config)
    elif covar == 'incbin.country':
        return covariates.BinnedEconomicCovariator(economicmodel, 2015, args, country_level=True, config=configs.merge(config, 'econcovar'))
    elif covar == 'loggdppc-shifted.country':
        return covariates.ShiftedEconomicCovariator(economicmodel, 2015, country_level=True, config=config)
    elif covar == 'ir-share':
        return covariates.ConstantCovariator('ir-share', irvalues.load_irweights("social/baselines/agriculture/world-combo-201710-irrigated-area.csv", 'irrigated_share'))
    elif '(' in covar:
        stack = []
        envstack = [{}]
        for cc in range(len(covar)):
            if covar[cc] == '(':
                stack.append(cc)
                envstack.append({})
            elif covar[cc] == ')':
                c0 = stack.pop()
                envstack.pop() # drop
                covariator = get_covariator(covar[c0+1:cc], args, weatherbundle, economicmodel, config=config, quiet=quiet, env=envstack[-1])
                varname = 'C' + str(len(envstack[-1])) + ('x' * (cc - c0 - 1))
                covar = covar[:c0] + varname + covar[cc+1:]
                envstack[-1][varname] = (covariator)
        return get_covariator(covar, args, weatherbundle, economicmodel, config=config, quiet=quiet, env=envstack[0])
    elif '*' in covar:
        sources = [get_covariator(x.strip(), args, weatherbundle, economicmodel, config=config, quiet=quiet, env=env) for x in covar.split('*', 1)]
        return covariates.ProductCovariator(sources[0], sources[1])
    elif '^' in covar:
        chunks = covar.split('^', 1)
        return covariates.PowerCovariator(get_covariator(chunks[0].strip(), args, weatherbundle, economicmodel, config=config, quiet=quiet, env=env), float(chunks[1]))
    elif covar[-4:] == 'clip':
        # Clip covariate to be between two bounds
        user_assert(len(args) == 2, f"clipping args must be len 2, got {args}")
        return covariates.ClipCovariator(get_covariator(covar[:-4], None, weatherbundle, economicmodel, config=config, quiet=quiet, env=env), args[0], args[1])
    elif covar[-6:] == 'spline':
        # Produces spline term covariates, named [name]spline1, [name]spline2, etc.
        return covariates.SplineCovariator(get_covariator(covar[:-6], None, weatherbundle, economicmodel, config=config, quiet=quiet, env=env), 'spline', args)
    elif covar[:8] == 'seasonal':
        seasondefs = config.get('covariate-season', config.get('within-season', None))
        return covariates.SeasonalWeatherCovariator(weatherbundle, 2015, seasondefs, covar[8:], config=configs.merge(config, 'climcovar'))
    elif covar[:4] == 'clim': # climtas, climcdd-20, etc.
        return covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 2015, covar[4:], config=configs.merge(config, 'climcovar'), usedaily=True, quiet=quiet), {covar: covar[4:]})
    elif covar[:6] == 'hierid':
        return covariates.populate_constantcovariator_by_hierid(covar, list(args))
    else:
        user_failure("Covariate %s is unknown." % covar)

def create_covariator(specconf, weatherbundle, economicmodel, config=None, quiet=False, farmer=None):
    """Interprets the entire covariates dictionary in the configuration file.

    Parameters
    ----------
    specconf : dict, optional
        Specification configuration.
    weatherbundle : generate.weather.DailyWeatherBundle
    economicmodel : adaptation.econmodel.SSPEconomicModel
    config : dict, optional
    quiet : bool, optional

    Returns
    -------
    covariator : adaptation.covariates.Covariator or None
    """
    if config is None:
        config = {}
    if parallel_weather.is_parallel(weatherbundle) and parallel_econmodel.is_parallel(economicmodel):
        return parallel_covariates.create_covariator(specconf, weatherbundle, economicmodel, farmer)
    if 'covariates' in specconf:
        assert isinstance(weatherbundle, DailyWeatherBundle)
        with weatherbundle.caching_baseline_values():
            covariators = []
            for covar in specconf['covariates']:
                fullconfig = configs.merge(config, specconf)
                covariators.append(get_covariator(covar, None, weatherbundle, economicmodel, config=fullconfig, quiet=quiet))
            
            if len(covariators) == 1:
                covariator = covariators[0]
            else:
                covariator = covariates.CombinedCovariator(covariators)
    else:
        covariator = None

    return covariator
        
def create_curvegen(csvv, covariator, regions, farmer='full', specconf=None, getcsvvcurve=False, diag_infix="", othermodels=None):
    """Create a CurveGenerator instance from specifications

    Parameters
    ----------
    csvv : dict
        Various parameters and curve descriptions from CSVV file.
    covariator : adaptation.covariates.Covariator or None
    regions : xarray.Dataset
    farmer : {'full', 'noadapt', 'incadapt'}, optional
        Type of farmer adaptation.
    specconf : dict, optional
        Specification configuration.
    getcsvvcurve : bool, optional
        If True, a adaptation.curvegen.CSVVCurveGenerator instance is returned.
    diag_infix : str
        Appended to the diagnostic suffix for CurveGenerators that report diagnostics.
    othermodels : dict, optional
        Previously created CurveGenerators that can be used here.

    Returns
    -------
    openest.generate.CurveGenerator
    """
    if specconf is None:
        specconf = {}
    if othermodels is None:
        othermodels = {}
    user_assert('depenunit' in specconf, "Specification configuration missing 'depenunit' string.")
    user_assert('functionalform' in specconf, "Specification configuration missing 'functionalform' string.")
    if specconf['functionalform'] in ['polynomial', 'cubicspline']:
        user_assert('indepunit' in specconf, "Specification configuration missing 'indepunit' string.")

    depenunit = specconf['depenunit']

    betalimits = specconf.get('beta-limits', {})
    betalimits = {key: list(map(float, betalimits[key].split(','))) for key in betalimits}

    if specconf['functionalform'] == 'polynomial':
        variable = specconf['variable']
        indepunit = specconf['indepunit']
        coeffvar = specconf.get('coeffvar', variable)

        if 'final-t' in specconf:
            suffix = '-' + str(specconf['suffixes'][specconf['final-t']])
        else:
            suffix = ''
            
        order = 0
        predinfix = ''
        for predname in csvv['prednames']:
            if predname == coeffvar + suffix:
                order = max(order, 1)
            else:
                match = re.match(coeffvar.replace('*', '\\*') + r'(\d+)' + suffix, predname)
                if match:
                    order = max(order, int(match.group(1)))
                    continue
                match = re.match(coeffvar.replace('*', '\\*') + r'-poly-(\d+)' + suffix, predname)
                if match:
                    predinfix = '-poly-'
                    order = max(order, int(match.group(1)))
                    continue

        if suffix:
            assert order > 1, "Cannot find more than one power of %sN%s in %s" % (coeffvar, suffix, str(csvv['prednames']))
        else:
            assert order > 1, "Cannot find more than one power of %s in %s" % (coeffvar, str(csvv['prednames']))
        
        weathernames = [variable] + ['%s-poly-%d' % (variable, power) for power in range(2, order+1)]
        if variables.needs_interpret(variable, specconf):
            weathernames = [variables.interpret_ds_transform(name, specconf) for name in weathernames]

        curr_curvegen = curvegen_known.PolynomialCurveGenerator([indepunit] + ['%s^%d' % (indepunit, pow) for pow in range(2, order+1)],
                                                                depenunit, coeffvar, order, csvv, diagprefix='coeff-' + diag_infix, predinfix=predinfix,
                                                                weathernames=weathernames, betalimits=betalimits, allow_raising=specconf.get('allow-raising', False))
        minfinder = lambda mintemp, maxtemp, sign: lambda curve: minpoly.findpolymin([0] + [sign * cc for cc in curve.coeffs], mintemp, maxtemp)

    elif specconf['functionalform'] == 'cubicspline':
        knots = specconf['knots']
        prefix = specconf['prefix']
        indepunit = specconf['indepunit']
        variable_name = specconf['variable']

        curr_curvegen = curvegen_known.CubicSplineCurveGenerator([indepunit] + ['%s^3' % indepunit] * (len(knots) - 2),
                                                                 depenunit, prefix, knots, variable_name, csvv, diagprefix='coeff-' + diag_infix,
                                                                 betalimits=betalimits)
        minfinder = lambda mintemp, maxtemp, sign: lambda curve: minspline.findsplinemin(knots, sign * np.asarray(curve.coeffs), mintemp, maxtemp)
        weathernames = curr_curvegen.weathernames[:]
    elif specconf['functionalform'] == 'coefficients':
        ds_transforms = {}
        indepunits = []
        transform_descriptions = []
        for name in specconf['variables']:
            if isinstance(specconf['variables'], Sequence):
                match = re.match(r"^(.+?)\s+\[(.+?)\]$", name)
                assert match is not None, "Could not find unit in %s" % name
                name = match.group(1)
            else:
                match = re.match(r"^(.+?)\s+\[(.+?)\]$", specconf['variables'][name])
                assert match is not None, "Could not find unit in %s" % specconf['variables'][name]
            ds_transforms[name] = variables.interpret_ds_transform(match.group(1), specconf)
            transform_descriptions.append(match.group(1))
            indepunits.append(match.group(2))

        # Only infer a univariate response if 1 variable
        if len(ds_transforms) == 1:
            # Reuse match.group(1), still set to our single variable
            univariate_transform, _ = variables.interpret_univariate_transform(match.group(1), specconf)
            if univariate_transform is None: # Cannot handle transform
                univariate_index = None
            else:
                univariate_index = 0
        else:
            univariate_index = univariate_transform = None

        curr_curvegen = curvegen_arbitrary.SumCoefficientsCurveGenerator(list(ds_transforms.keys()), ds_transforms,
                                                                         transform_descriptions, indepunits, depenunit,
                                                                         csvv, diagprefix='coeff-' + diag_infix, betalimits=betalimits,
                                                                         univariate_index=univariate_index,
                                                                         univariate_transform=univariate_transform)
        weathernames = [] # Use curve directly
    elif specconf['functionalform'] == 'sum-by-time':
        if specconf['subspec']['functionalform'] in ['polynomial', 'coefficients']:
            subspecconf = configs.merge(specconf, specconf['subspec'])
            csvvcurvegen = create_curvegen(csvv, None, regions, farmer=farmer, specconf=subspecconf, getcsvvcurve=True) # don't pass covariator, so skip farmer curvegen
            if isinstance(csvvcurvegen, curvegen_known.PolynomialCurveGenerator):
                sumbytime_constructor = curvegen_known.SumByTimePolynomialCurveGenerator
            elif isinstance(csvvcurvegen, curvegen_arbitrary.SumCoefficientsCurveGenerator):
                sumbytime_constructor = curvegen_arbitrary.SumByTimeCoefficientsCurveGenerator
            else:
                raise ValueError("Error: Curve-generator resulted in a " + str(csvvcurvegen.__class__))
            
            if 'suffixes' in specconf:
                curr_curvegen = sumbytime_constructor(csvv, csvvcurvegen, specconf['suffixes'], diagprefix='coeff-' + diag_infix)
            elif 'suffix-triangle' in specconf:
                assert 'within-season' in specconf
                suffix_triangle = specconf['suffix-triangle']
                for rr in range(len(suffix_triangle)):
                    assert isinstance(suffix_triangle, Sequence) and len(suffix_triangle[rr]) == rr + 1

                culture_map = irvalues.get_file_cached(specconf['within-season'], irvalues.load_culture_months)
                get_curvegen = lambda suffixes: sumbytime_constructor(csvv, csvvcurvegen, suffixes, diagprefix='coeff-' + diag_infix)
                
                curr_curvegen = curvegen.SeasonTriangleCurveGenerator(culture_map, get_curvegen=get_curvegen, suffix_triangle=suffix_triangle)
            else:
                raise AssertionError("Either 'suffixes' or 'suffix-triangle' required for functional form 'sum-by-time'.")
        else:
            assert 'suffixes' in specconf, "Only 'suffixes' is allowed for arbitrary subform with 'sum-by-time'."
            print("WARNING: Sum-by-time is being performed reductively. Efficiency improvements possible.")
            
            csvvcurvegens = []
            for tt in range(len(specconf['suffixes'])):
                subspecconf = configs.merge(specconf, specconf['subspec'])
                subspecconf['final-t'] = tt # timestep of weather; also used by subspec to get suffix
                csvvcurvegen = create_curvegen(csvv, None, regions, farmer=farmer, specconf=subspecconf, getcsvvcurve=True) # don't pass covariator, so skip farmer curvegen
                assert isinstance(csvvcurvegen, curvegen.CSVVCurveGenerator), "Error: Curve-generator resulted in a " + str(csvvcurvegen.__class__)
                csvvcurvegens.append(csvvcurvegen)
            curr_curvegen = curvegen.SumCurveGenerator(csvvcurvegens, specconf['suffixes'])

        weathernames = [] # Use curve directly
    else:
        user_failure("Unknown functional form %s." % specconf['functionalform'])

    if getcsvvcurve:
        return curr_curvegen
        
    if specconf.get('goodmoney', False):
        baselineloggdppcs = {}
        for region in regions:
            baselineloggdppcs[region] = covariator.get_current(region)['loggdppc']

    # Clause to set curve baseline extents if configured.
    clipping_cfg = specconf.get('clipping', False)
    if clipping_cfg:
        # Validate clipping configuration option.
        user_assert(clipping_cfg in ['boatpose', 'downdog', True, 'corpsepose', 'plankpose'],
                    "unknown option for configuration key 'clipping'")
        if clipping_cfg in ['corpsepose', 'plankpose']:
            user_assert(specconf.get('grounding', False) in ['min', 'max'],
                        "The 'grounding' option must be either 'min' or 'max'")

        # Grab temperature window to search for curve extrema.
        mintemp = specconf.get('clip-mintemp', 10)
        maxtemp = specconf.get('clip-maxtemp', 25)

        # Determine extrema value of curve within temperature window.
        if clipping_cfg == 'boatpose' or clipping_cfg is True:
            curve_extrema = minfinder(mintemp, maxtemp, 1)
            get_baselineextrema = constraints.get_curve_minima
        elif clipping_cfg == 'downdog':
            curve_extrema = minfinder(mintemp, maxtemp, -1)
            get_baselineextrema = constraints.get_curve_maxima
        elif clipping_cfg in ['corpsepose', 'plankpose']:
            pass
        else:
            user_failure("unknown option for configuration key 'clipping'")

        if covariator:
            _, baselineexts = get_baselineextrema(
                regions, curr_curvegen, covariator,
                mintemp, maxtemp,
                analytic=curve_extrema
            )
        else:
            curve = curr_curvegen.get_curve('global', 2000, {})
            curve_global_extrema = curve_extrema(curve)
            baselineexts = {r: curve_global_extrema for r in regions}

    def transform(region, curve):
        if isinstance(curve, smart_curve.SmartCurve):
            final_curve = curve
        else:
            final_curve = smart_curve.CoefficientsCurve(curve.ccs, weathernames)

        if (clipping_cfg and clipping_cfg in ['boatpose', 'downdog', True]) or specconf.get('goodmoney'):
            final_curve = smart_curve.ShiftedCurve(final_curve, -final_curve.univariate(baselineexts[region]))

        if 'goodmoney' in specconf: 
            gm = specconf.get('goodmoney')
            if gm == 'more-is-good':
                gm_curve = smart_curve.MaximumCurve
            elif gm in ['less-is-good', True] :
                gm_curve = smart_curve.MinimumCurve
            else:
                user_failure('the goodmoney option must be one of more-is-good, less-is-good, yes or True')
            covars = covariator.get_current(region)
            covars['loggdppc'] = baselineloggdppcs[region]
            noincadapt_unshifted_curve = curr_curvegen.get_curve(region, None, covars, recorddiag=False)
            if not isinstance(noincadapt_unshifted_curve, smart_curve.SmartCurve):
                noincadapt_unshifted_curve = smart_curve.CoefficientsCurve(noincadapt_unshifted_curve.ccs, weathernames)
            noincadapt_curve = smart_curve.ShiftedCurve(noincadapt_unshifted_curve, -noincadapt_unshifted_curve.univariate(baselineexts[region]))            
            final_curve = gm_curve(final_curve, noincadapt_curve)

        # Clause for additional curve clipping transforms, if configured.
        if clipping_cfg:
            if clipping_cfg is True:
                final_curve = smart_curve.ClippedCurve(final_curve, cliplow=True)
            elif clipping_cfg in ['boatpose', 'downdog']:
                if clipping_cfg == 'boatpose':
                    cliplow = True
                    ucurve_direction = 'boatpost'
                elif clipping_cfg == 'downdog':
                    cliplow = False
                    ucurve_direction = 'downdog'

                final_curve = ushape_numeric.UShapedDynamicCurve(
                    smart_curve.ClippedCurve(final_curve, cliplow),
                    midtemp=baselineexts[region],
                    gettas=lambda ds: ds[weathernames[0]].data,  # Grab independent variable data, at [0].
                    unicurve=final_curve.univariate,
                    direction=ucurve_direction,
                )
            else: # 'corpsepose' or 'plankpose'
                clipmodel = specconf.get('clip-model')
                user_assert(clipmodel, "The 'clip-model' config option is required for corpsepose or plankpose clipping.")
                user_assert(clipmodel in othermodels, "The requested 'clip-model' was not previously defined in the specifications list.")
                assert isinstance(othermodels[clipmodel], curvegen.DelayedCurveGenerator), "Clipping CurveGenerator must have a saved curve."
                if clipping_cfg == 'corpsepose':
                    final_curve = smart_curve.MinimumCurve(final_curve, othermodels[clipmodel].current_curves[region])
                else: # plankpose
                    final_curve = smart_curve.MaximumCurve(final_curve, othermodels[clipmodel].current_curves[region])

        if specconf.get('extrapolation', False):
            exargs = specconf['extrapolation']
            assert 'indepvar' in exargs or 'indepvars' in exargs
            indepvars = exargs.get('indepvars', [exargs['indepvar']])
            
            assert 'margin' in exargs or 'margins' in exargs
            if 'margin' in exargs:
                assert len(indepvars) == 1
                margins = {indepvars[0]: exargs['margin']}
            else:
                margins = {indepvars[ii]: exargs['margins'][ii] for ii in range(len(indepvars))}

            assert 'bounds' in exargs
            if 'bounds' in exargs and isinstance(exargs['bounds'], tuple) or (isinstance(exargs['bounds'], Sequence) and len(exargs['bounds']) == 2 and (isinstance(exargs['bounds'][0], float) or isinstance(exargs['bounds'][0], int))):
                bounds = [(exargs['bounds'][0],), (exargs['bounds'][1],)]
            else:
                bounds = exargs['bounds']
            final_curve = LinearExtrapolationCurve(final_curve, indepvars, bounds, margins, exargs.get('scaling', 1))

        return final_curve

    if clipping_cfg and specconf.get('goodmoney', False):
        final_curvegen = curvegen.TransformCurveGenerator(transform, "Clipping and Good Money transformation", curr_curvegen)
    elif clipping_cfg:
        final_curvegen = curvegen.TransformCurveGenerator(transform, "Clipping transformation", curr_curvegen)
    elif specconf.get('goodmoney', False):
        final_curvegen = curvegen.TransformCurveGenerator(transform, "Good Money transformation", curr_curvegen)
    else:
        final_curvegen = curvegen.TransformCurveGenerator(transform, "Smart curve transformation", curr_curvegen)
        final_curvegen.deltamethod_passthrough = True

    if covariator:
        final_curvegen = curvegen.FarmerCurveGenerator(final_curvegen, covariator, farmer)

    return final_curvegen

def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full', specconf=None, config=None):
    """

    Parameters
    ----------
    csvv : dict
        Various parameters and curve descriptions from CSVV file.
    weatherbundle : generate.weather.DailyWeatherBundle
    economicmodel : adaptation.econmodel.SSPEconomicModel
    qvals : generate.pvalses.ConstantDictionary
    farmer : {'full', 'noadapt', 'incadapt'}, optional
        Type of farmer adaptation.
    specconf : dict, optional
        Specification configuration.
    config : dict, optional

    Returns
    -------
    calculation : openest.generate.stdlib.SpanInstabase
    list
    object
    """
    if specconf is None:
        specconf = {}
    if config is None:
        config = {}
    user_assert('depenunit' in specconf, "Specification configuration missing 'depenunit' string.")
    user_assert('calculation' in specconf, "Specification configuration missing 'calculation' list.")
    user_assert('description' in specconf, "Specification configuration missing 'description' list.")


    if config.get('report-variance', False):
        csvv['gamma'] = np.zeros(len(csvv['gamma'])) # So no mistaken results
    else:
        csvvfile.collapse_bang(
            csvv,
            seed=qvals.get_seed('csvv'),
            method=config.get("mvn-method", "svd")
        )
    
    depenunit = specconf['depenunit']
    
    covariator = create_covariator(specconf, weatherbundle, economicmodel, config, farmer=farmer)

    # Subset to regions (i.e. hierids) to act on.
    target_regions = configs.get_regions(weatherbundle.regions, config.get('filter-region'))

    final_curvegen = create_curvegen(csvv, covariator, target_regions, farmer=farmer, specconf=specconf)

    extras = dict(output_unit=depenunit, units=depenunit, curve_description=specconf['description'], errorvar=csvvfile.get_errorvar(csvv))
    calculation = calculator.create_postspecification(specconf['calculation'], {'default': final_curvegen}, None, extras=extras)
        
    if covariator is None:
        return calculation, [], lambda region: {}
    else:
        return calculation, [], covariator.get_current
