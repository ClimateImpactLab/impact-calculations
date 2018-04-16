import re
from adaptation import csvvfile, curvegen, curvegen_known, curvegen_arbitrary, covariates, constraints
from datastore import irvalues
from openest.generate import smart_curve, selfdocumented
from openest.models.curve import ShiftedCurve, MinimumCurve, ClippedCurve, ZeroInterceptPolynomialCurve
from openest.generate.stdlib import *
from impactcommon.math import minpoly, minspline
import calculator, variables, configs

def user_failure(message):
    print "ERROR: " + message
    exit()

def user_assert(check, message):
    if not check:
        user_failure(message)

def get_covariator(covar, args, weatherbundle, economicmodel, config={}, quiet=False):
    if isinstance(covar, dict):
        return get_covariator(covar.keys()[0], covar.values()[0], weatherbundle, economicmodel, config=config, quiet=quiet)
    elif covar in ['loggdppc', 'logpopop']:
        return covariates.EconomicCovariator(economicmodel, 2015, config=config)
    elif covar == 'incbin':
        return covariates.BinnedEconomicCovariator(economicmodel, 2015, args, config=config)
    elif covar == 'ir-share':
        return covariates.ConstantCovariator('ir-share', irvalues.load_irweights("social/baselines/agriculture/world-combo-201710-irrigated-area.csv", 'irrigated_share'))
    elif '*' in covar:
        sources = map(lambda x: get_covariator(x.strip(), args, weatherbundle, economicmodel, config=config, quiet=quiet), covar.split('*', 1))
        return covariates.ProductCovariator(sources[0], sources[1])
    elif covar[:8] == 'seasonal':
        return covariates.SeasonalWeatherCovariator(weatherbundle, 2015, config['within-season'], covar[8:], config)
    elif covar[:4] == 'clim': # climtas, climcdd-20, etc.
        return covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 2015, covar[4:], config=config, quiet=quiet), {covar: covar[4:]})
    elif '^' in covar:
        chunks = covar.split('^', 1)
        return covariates.PowerCovariator(get_covariator(chunks[0].strip(), args, weatherbundle, economicmodel, config=config, quiet=quiet), float(chunks[1]))
    else:
        user_failure("Covariate %s is unknown." % covar)
        
def create_covariator(specconf, weatherbundle, economicmodel, config={}, quiet=False):
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
        
def create_curvegen(csvv, covariator, regions, farmer='full', specconf={}):
    user_assert('depenunit' in specconf, "Specification configuration missing 'depenunit' string.")
    user_assert('functionalform' in specconf, "Specification configuration missing 'functionalform' string.")
    if specconf['functionalform'] in ['polynomial', 'cubicspline']:
        user_assert('indepunit' in specconf, "Specification configuration missing 'indepunit' string.")

    depenunit = specconf['depenunit']

    if specconf['functionalform'] == 'polynomial':
        variable = specconf['variable']
        indepunit = specconf['indepunit']
        
        order = 0
        predinfix = ''
        for predname in csvv['prednames']:
            if predname == variable:
                order = max(order, 1)
            else:
                match = re.match(variable + r'(\d+)', predname)
                if match:
                    order = max(order, int(match.group(1)))
                    continue
                match = re.match(variable + r'-poly-(\d+)', predname)
                if match:
                    predinfix = '-poly-'
                    order = max(order, int(match.group(1)))
                    continue

        assert order > 1
                    
        weathernames = [variable] + ['%s-poly-%d' % (variable, power) for power in range(2, order+1)]
        if 'within-season' in specconf:
            weathernames = [selfdocumented.DocumentedFunction(lambda ds: variables.post_process(ds, name, specconf), None, "Limit to within season", name) for name in weathernames]

        curr_curvegen = curvegen_known.PolynomialCurveGenerator([indepunit] + ['%s^%d' % (indepunit, pow) for pow in range(2, order+1)],
                                                                depenunit, variable, order, csvv, predinfix=predinfix, weathernames=weathernames)
        minfinder = lambda mintemp, maxtemp: lambda curve: minpoly.findpolymin([0] + curve.ccs, mintemp, maxtemp)
            
    elif specconf['functionalform'] == 'cubic spline':
        knots = specconf['knots']
        prefix = specconf['prefix']
        indepunit = specconf['indepunit']

        curr_curvegen = curvegen_known.CubicSplineCurveGenerator([indepunit] + ['%s^3' % indepunit] * (len(knots) - 2),
                                                             depenunit, prefix, knots, csvv)
        minfinder = lambda mintemp, maxtemp: lambda curve: minspline.findsplinemin(knots, curve.coeffs, mintemp, maxtemp)
        weathernames = [prefix]
    elif specconf['functionalform'] == 'coefficients':
        ds_transforms = {}
        indepunits = []
        transform_descriptions = []
        for name in specconf['variables']:
            match = re.match(r"^(.+?)\s+\[(.+?)\]$", specconf['variables'][name])
            assert match is not None, "Could not find unit in %s" % specconf['variables'][name]
            ds_transforms[name] = variables.interpret_ds_transform(match.group(1), specconf)
            transform_descriptions.append(match.group(1))
            indepunits.append(match.group(2))

        curr_curvegen = curvegen_arbitrary.SumCoefficientsCurveGenerator(ds_transforms.keys(), ds_transforms, transform_descriptions, indepunits, depenunit, csvv)
        weathernames = [] # Use curve directly
    else:
        user_failure("Unknown functional form %s." % specconf['functionalform'])

    if specconf.get('goodmoney', False):
        baselineloggdppcs = {}
        for region in regions:
            baselineloggdppcs[region] = covariator.get_current(region)['loggdppc']

    if specconf.get('clipping', False):
        mintemp = specconf.get('clip-mintemp', 10)
        maxtemp = specconf.get('clip-maxtemp', 25)
        # Determine minimum value of curve between 10C and 25C
        if covariator:
            baselinecurves, baselinemins = constraints.get_curve_minima(regions, curr_curvegen, covariator,
                                                                        mintemp, maxtemp, minfinder(mintemp, maxtemp))
        else:
            curve = curr_curvegen.get_curve('global', 2000, {})
            curvemin = minfinder(mintemp, maxtemp)(curve)
            baselinemins = {region: curvemin for region in regions}

    def transform(region, curve):
        if isinstance(curve, ZeroInterceptPolynomialCurve):
            final_curve = smart_curve.ZeroInterceptPolynomialCurve(curve.ccs, weathernames, specconf.get('allow-raising', False))
        elif isinstance(curve, smart_curve.SmartCurve):
            final_curve = curve
        else:
            final_curve = smart_curve.CoefficientsCurve(curve.ccs, weathernames)

        if specconf.get('clipping', False):
            final_curve = ShiftedCurve(final_curve, -curve(baselinemins[region]))

        if specconf.get('goodmoney', False):
            covars = covariator.get_current(region)
            covars['loggdppc'] = baselineloggdppcs[region]
            noincadapt_unshifted_curve = curr_curvegen.get_curve(region, None, covars, recorddiag=False)
            if len(weathernames) > 1:
                coeff_noincadapt_unshifted_curve = CoefficientsCurve(noincadapt_unshifted_curve.ccs, weathernames)
            else:
                coeff_noincadapt_unshifted_curve = noincadapt_unshifted_curve
            noincadapt_curve = ShiftedCurve(coeff_noincadapt_unshifted_curve, -noincadapt_unshifted_curve(baselinemins[region]))

            final_curve = MinimumCurve(final_curve, noincadapt_curve)

        if specconf.get('clipping', False):
            return ClippedCurve(final_curve)
        else:
            return final_curve

    if specconf.get('clipping', False) and specconf.get('goodmoney', False):
        final_curvegen = curvegen.TransformCurveGenerator(transform, "Clipping and Good Money transformation", curr_curvegen)
    elif specconf.get('clipping', False):
        final_curvegen = curvegen.TransformCurveGenerator(transform, "Clipping transformation", curr_curvegen)
    elif specconf.get('goodmoney', False):
        final_curvegen = curvegen.TransformCurveGenerator(transform, "Good Money transformation", curr_curvegen)
    else:
        final_curvegen = curvegen.TransformCurveGenerator(transform, None, curr_curvegen)

    if covariator:
        final_curvegen = curvegen.FarmerCurveGenerator(final_curvegen, covariator, farmer)

    return final_curvegen

def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full', specconf={}, config={}):
    user_assert('depenunit' in specconf, "Specification configuration missing 'depenunit' string.")
    user_assert('calculation' in specconf, "Specification configuration missing 'calculation' list.")
    user_assert('description' in specconf, "Specification configuration missing 'description' list.")

    csvvfile.collapse_bang(csvv, qvals.get_seed())
    
    depenunit = specconf['depenunit']
    
    covariator = create_covariator(specconf, weatherbundle, economicmodel, config)
    final_curvegen = create_curvegen(csvv, covariator, weatherbundle.regions, farmer=farmer, specconf=specconf)

    extras = dict(output_unit=depenunit, units=depenunit, curve_description=specconf['description'])
    calculation = calculator.create_postspecification(specconf['calculation'], {'default': final_curvegen}, None, extras=extras)
        
    if covariator is None:
        return calculation, [], lambda: {}
    else:
        return calculation, [], covariator.get_current
