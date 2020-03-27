"""Interpret the specifications sections of a configuration file.

As we define them, specifications are segments of the full
specification used by a sector's projection. For example, a projection
can consist of one polynomial specification applied to temperatures
over 20C and another for temperatures below 20C; or one polynomial
specification can be used for temperature and another for
precipitation.
"""

import re
from adaptation import csvvfile, curvegen, curvegen_known, curvegen_arbitrary, covariates, constraints
from datastore import irvalues
from openest.generate import smart_curve, selfdocumented
from openest.models.curve import ShiftedCurve, MinimumCurve, ClippedCurve
from openest.generate.stdlib import *
from impactcommon.math import minpoly, minspline
from openest.curves import ushape_numeric
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

def get_covariator(covar, args, weatherbundle, economicmodel, config={}, quiet=False):
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

    Returns
    -------
    adaptation.covariates.Covariator
    """
    if isinstance(covar, dict):
        return get_covariator(list(covar.keys())[0], list(covar.values())[0], weatherbundle, economicmodel, config=config, quiet=quiet)
    elif covar in ['loggdppc', 'logpopop', 'year']:
        return covariates.EconomicCovariator(economicmodel, 2015, config=configs.merge(config, 'econcovar'))
    elif covar == 'incbin':
        return covariates.BinnedEconomicCovariator(economicmodel, 2015, args, config=configs.merge(config, 'econcovar'))
    elif covar == 'loggdppc-shifted':
        return covariates.ShiftedEconomicCovariator(economicmodel, 2015, config)
    elif covar == 'ir-share':
        return covariates.ConstantCovariator('ir-share', irvalues.load_irweights("social/baselines/agriculture/world-combo-201710-irrigated-area.csv", 'irrigated_share'))
    elif '*' in covar:
        sources = [get_covariator(x.strip(), args, weatherbundle, economicmodel, config=config, quiet=quiet) for x in covar.split('*', 1)]
        return covariates.ProductCovariator(sources[0], sources[1])
    elif '^' in covar:
        chunks = covar.split('^', 1)
        return covariates.PowerCovariator(get_covariator(chunks[0].strip(), args, weatherbundle, economicmodel, config=config, quiet=quiet), float(chunks[1]))
    elif covar[-6:] == 'spline':
        # Produces spline term covariates, named [name]spline1, [name]spline2, etc.
        return covariates.SplineCovariator(get_covariator(covar[:-6], None, weatherbundle, economicmodel, config=config, quiet=quiet), covar[:-6], 'spline', args)
    elif covar[:8] == 'seasonal':
        return covariates.SeasonalWeatherCovariator(weatherbundle, 2015, config['within-season'], covar[8:], config=configs.merge(config, 'climcovar'))
    elif covar[:4] == 'clim': # climtas, climcdd-20, etc.
        return covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 2015, covar[4:], config=configs.merge(config, 'climcovar'), usedaily=True, quiet=quiet), {covar: covar[4:]})
    elif covar[:6] == 'hierid':
        return covariates.populate_constantcovariator_by_hierid(covar, list(args))
    else:
        user_failure("Covariate %s is unknown." % covar)

def create_covariator(specconf, weatherbundle, economicmodel, config={}, quiet=False):
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
    if 'covariates' in specconf:
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
        
def create_curvegen(csvv, covariator, regions, farmer='full', specconf={}, getcsvvcurve=False):
    """Create a CurveGenerator instance from specifications

    Parameters
    ----------
    csvv : dict
        Various parameters and curve descriptions from CSVV file.
    covariator : adaptation.covariates.Covariator
    regions : xarray.Dataset
    farmer : {'full', 'noadapt', 'incadapt'}, optional
        Type of farmer adaptation.
    specconf : dict, optional
        Specification configuration.
    getcsvvcurve : bool, optional
        If True, a adaptation.curvegen.CSVVCurveGenerator instance is returned.

    Returns
    -------
    openest.generate.CurveGenerator
    """
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
                                                                depenunit, coeffvar, order, csvv, predinfix=predinfix,
                                                                weathernames=weathernames, betalimits=betalimits, allow_raising=specconf.get('allow-raising', False))
        minfinder = lambda mintemp, maxtemp, sign: lambda curve: minpoly.findpolymin([0] + [sign * cc for cc in curve.coeffs], mintemp, maxtemp)

    elif specconf['functionalform'] == 'cubicspline':
        knots = specconf['knots']
        prefix = specconf['prefix']
        indepunit = specconf['indepunit']
        variable_name = specconf['variable']

        curr_curvegen = curvegen_known.CubicSplineCurveGenerator([indepunit] + ['%s^3' % indepunit] * (len(knots) - 2),
                                                                 depenunit, prefix, knots, variable_name, csvv, betalimits=betalimits)
        minfinder = lambda mintemp, maxtemp, sign: lambda curve: minspline.findsplinemin(knots, sign * curve.coeffs, mintemp, maxtemp)
        weathernames = [prefix]
    elif specconf['functionalform'] == 'coefficients':
        ds_transforms = {}
        indepunits = []
        transform_descriptions = []
        for name in specconf['variables']:
            if isinstance(specconf['variables'], list):
                match = re.match(r"^(.+?)\s+\[(.+?)\]$", name)
                assert match is not None, "Could not find unit in %s" % name
                name = match.group(1)
            else:
                match = re.match(r"^(.+?)\s+\[(.+?)\]$", specconf['variables'][name])
                assert match is not None, "Could not find unit in %s" % specconf['variables'][name]
            ds_transforms[name] = variables.interpret_ds_transform(match.group(1), specconf)
            transform_descriptions.append(match.group(1))
            indepunits.append(match.group(2))

        curr_curvegen = curvegen_arbitrary.SumCoefficientsCurveGenerator(list(ds_transforms.keys()), ds_transforms,
                                                                         transform_descriptions, indepunits, depenunit,
                                                                         csvv, betalimits=betalimits)
        weathernames = [] # Use curve directly
    elif specconf['functionalform'] == 'sum-by-time':
        csvvcurvegens = []
        for tt in range(len(specconf['suffixes'])):
            subspecconf = configs.merge(specconf, specconf['subspec'])
            subspecconf['final-t'] = tt
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

    if specconf.get('clipping', False):
        mintemp = specconf.get('clip-mintemp', 10)
        maxtemp = specconf.get('clip-maxtemp', 25)
        # Determine minimum value of curve between 10C and 25C
        if covariator:
            if specconf['clipping'] == 'boatpose' or specconf['clipping'] == True:
                baselinecurves, baselineexts = constraints.get_curve_minima(regions, curr_curvegen, covariator,
                                                                            mintemp, maxtemp, minfinder(mintemp, maxtemp, 1))
            elif specconf['clipping'] == 'downdog':
                baselinecurves, baselineexts = constraints.get_curve_maxima(regions, curr_curvegen, covariator,
                                                                            mintemp, maxtemp, minfinder(mintemp, maxtemp, -1))
            else:
                assert False, "Unknown option for configuration key 'clipping'."
        else:
            curve = curr_curvegen.get_curve('global', 2000, {})
            if specconf['clipping'] == 'boatpose' or specconf['clipping'] == True:
                curvemin = minfinder(mintemp, maxtemp, 1)(curve)
            elif specconf['clipping'] == 'downdog':
                curvemin = minfinder(mintemp, maxtemp, -1)(curve)
            else:
                assert False, "Unknown option for configuration key 'clipping'."
                
            baselineexts = {region: curvemin for region in regions}

    def transform(region, curve):
        if isinstance(curve, smart_curve.SmartCurve):
            final_curve = curve
        else:
            final_curve = smart_curve.CoefficientsCurve(curve.ccs, weathernames)

        if specconf.get('clipping', False):
            final_curve = ShiftedCurve(final_curve, -curve.get_univariate()(baselineexts[region]))

        if specconf.get('goodmoney', False):
            covars = covariator.get_current(region)
            covars['loggdppc'] = baselineloggdppcs[region]
            noincadapt_unshifted_curve = curr_curvegen.get_curve(region, None, covars, recorddiag=False)
            if len(weathernames) > 1:
                coeff_noincadapt_unshifted_curve = CoefficientsCurve(noincadapt_unshifted_curve.ccs, weathernames)
            else:
                coeff_noincadapt_unshifted_curve = noincadapt_unshifted_curve
            noincadapt_curve = ShiftedCurve(coeff_noincadapt_unshifted_curve, -noincadapt_unshifted_curve(baselineexts[region]))

            final_curve = MinimumCurve(final_curve, noincadapt_curve)

        if specconf.get('clipping', False) == True:
            return ClippedCurve(final_curve)
        elif specconf.get('clipping', False) == 'boatpose':
            final_curve = ClippedCurve(final_curve)
            return ushape_numeric.UShapedCurveDynamic(final_curve, baselineexts[region], lambda ds: ds[weathernames[0]], final_curve.get_univariate())
        elif specconf.get('clipping', False) == 'downdog':
            final_curve = ClippedCurve(final_curve, cliplow=False)
            return ushape_numeric.UShapedCurveDynamic(final_curve, baselineexts[region], lambda ds: ds[weathernames[0]], final_curve.get_univariate(), direction='downdog')
        else:
            return final_curve

    if specconf.get('clipping', False) and specconf.get('goodmoney', False):
        final_curvegen = curvegen.TransformCurveGenerator(transform, "Clipping and Good Money transformation", curr_curvegen)
    elif specconf.get('clipping', False):
        final_curvegen = curvegen.TransformCurveGenerator(transform, "Clipping transformation", curr_curvegen)
    elif specconf.get('goodmoney', False):
        final_curvegen = curvegen.TransformCurveGenerator(transform, "Good Money transformation", curr_curvegen)
    else:
        final_curvegen = curvegen.TransformCurveGenerator(transform, "Smart curve transformation", curr_curvegen)
        final_curvegen.deltamethod_passthrough = True

    if covariator:
        final_curvegen = curvegen.FarmerCurveGenerator(final_curvegen, covariator, farmer)

    return final_curvegen

def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full', specconf={}, config={}):
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
    user_assert('depenunit' in specconf, "Specification configuration missing 'depenunit' string.")
    user_assert('calculation' in specconf, "Specification configuration missing 'calculation' list.")
    user_assert('description' in specconf, "Specification configuration missing 'description' list.")

    if config.get('report-variance', False):
        csvv['gamma'] = np.zeros(len(csvv['gamma'])) # So no mistaken results
    else:
        csvvfile.collapse_bang(csvv, qvals.get_seed('csvv'))
    
    depenunit = specconf['depenunit']
    
    covariator = create_covariator(specconf, weatherbundle, economicmodel, config)
    final_curvegen = create_curvegen(csvv, covariator, weatherbundle.regions, farmer=farmer, specconf=specconf)

    extras = dict(output_unit=depenunit, units=depenunit, curve_description=specconf['description'])
    calculation = calculator.create_postspecification(specconf['calculation'], {'default': final_curvegen}, None, extras=extras)
        
    if covariator is None:
        return calculation, [], lambda region: {}
    else:
        return calculation, [], covariator.get_current
