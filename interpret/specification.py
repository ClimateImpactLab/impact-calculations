import re
from adaptation import csvvfile, curvegen, curvegen_known, covariates, constraints
from openest.generate.smart_curve import CoefficientsCurve
from openest.models.curve import ShiftedCurve, MinimumCurve, ClippedCurve
from openest.generate.stdlib import *
from impactcommon.math import minpoly, minspline

def user_failure(message):
    print "ERROR: " + message
    exit()

def user_assert(check, message):
    if not check:
        user_failure(message)

def create_covariator(specconf, weatherbundle, economicmodel, config={}):
    if 'covariates' in specconf:
        covariators = []
        for covar in specconf['covariates']:
            if covar in ['loggdppc', 'logpopop']:
                covariators.append(covariates.EconomicCovariator(economicmodel, 2015, config=config))
            elif covar == 'incbin':
                covariators.append(covariates.BinnedEconomicCovariator(economicmodel, 2015, specconf['covariates'][covar], config=config))
            elif covar == 'climtas':
                covariators.append(covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 2015, 'tas', config=config), {'climtas': 'tas'}))
            else:
                user_failure("Covariate %s is unknown." % covar)
            
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

    depenunit = specconf['depenunit']

    if specconf['functionalform'] == 'polynomial':
        variable = specconf['variable']
        indepunit = specconf['indepunit']
        
        order = 0
        for predname in csvv['prednames']:
            if predname == variable:
                order = max(order, 1)
            else:
                match = re.match(variable + r'(\d+)', predname)
                if match:
                    order = max(order, int(match.group(1)))
                else:
                    user_failure("Predictor %s not interpretable for %s." % (predname, specconf['functionalform']))
                    
        curr_curvegen = curvegen_known.PolynomialCurveGenerator([indepunit] + ['%s^%d' % (indepunit, pow) for pow in range(2, order+1)],
                                                                depenunit, variable, order, csvv)
        minfinder = lambda mintemp, maxtemp: lambda curve: minpoly.findpolymin([0] + curve.ccs, mintemp, maxtemp)
        weathernames = ['tas'] + ['tas-poly-%d' % power for power in range(2, order+1)]
    elif specconf['functionalform'] == 'cubic spline':
        knots = specconf['knots']
        prefix = specconf['prefix']
        indepunit = specconf['indepunit']

        curr_curvegen = curvegen_known.CubicSplineCurveGenerator([indepunit] + ['%s^3' % indepunit] * (len(knots) - 2),
                                                             depenunit, prefix, knots, csvv)
        minfinder = lambda mintemp, maxtemp: lambda curve: minspline.findsplinemin(knots, curve.coeffs, mintemp, maxtemp)
        weathernames = ['tas']
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
        if len(weathernames) > 1:
            final_curve = CoefficientsCurve(curve.ccs, weathernames)
        else:
            final_curve = curve

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

    final_curvegen = curvegen.TransformCurveGenerator(transform, "Clipping and/or Good Money", curr_curvegen)

    if covariator:
        final_curvegen = curvegen.FarmerCurveGenerator(final_curvegen, covariator, farmer)

    return final_curvegen

def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full', specconf={}, config={}):
    user_assert('depenunit' in specconf, "Specification configuration missing 'depenunit' string.")
    user_assert('description' in specconf, "Specification configuration missing 'description' string.")

    csvvfile.collapse_bang(csvv, qvals.get_seed())
    
    depenunit = specconf['depenunit']
    
    covariator = create_covariator(specconf, weatherbundle, economicmodel, config)
    final_curvegen = create_curvegen(csvv, covariator, weatherbundle.regions, farmer=farmer, specconf=specconf)
    
    calculation = YearlyAverageDay(depenunit, final_curvegen, specconf['description'])
        
    if covariator is None:
        return calculation, [], lambda: {}
    else:
        return calculation, [], covariator.get_current
