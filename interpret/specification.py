import re
from adaptation import csvvfile, curvegen, curvegen_known, covariates, constraints
from openest.models.curve import CoefficientsCurve, ShiftedCurve, CoefficientsCurve, MinimumCurve, ClippedCurve
from openest.generate.stdlib import *
from impactcommon import math

def user_failure(message):
    print "ERROR: " + message
    exit()

def user_assert(check, message):
    if not check:
        user_failure(message)
    
def prepare(specconf, csvv, weatherbundle, economicmodel, qvals):
    user_assert('covariates' in specconf, "Specification configuration missing 'covariates' list.")
    user_assert('depenunit' in specconf, "Specification configuration missing 'depenunit' string.")
    user_assert('functionalform' in specconf, "Specification configuration missing 'functionalform' string.")
    user_assert('description' in specconf, "Specification configuration missing 'description' string.")
    
    csvvfile.collapse_bang(csvv, qvals.get_seed('csvv'))

    covariators = []
    for covar in specconf['covariates']:
        if covar == 'loggdppc':
            covariators.append(covariates.EconomicCovariator(economicmodel, 2015))
        elif covar == 'climtas':
            covariators.append(covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 2015, 'tas'), {'climtas': 'tas'}))
        else:
            user_failure("Covariate %s is unknown." % covar)

    if len(covariators) == 1:
        covariator = covariators[0]
    else:
        covariator = covariates.CombinedCovariator(covariators)
    
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
                    
        curvegen = curvegen_known.PolynomialCurveGenerator([indepunit] + ['%s^%d' % (unit, pow) for pow in range(2, order+1)],
                                                           depenunit, variable, order, csvv)
        minfinder = lambda mintemp, maxtemp: lambda curve: math.minpoly.findpolymin([0] + curve.ccs, mintemp, maxtemp)
    elif specconf['functionalform'] == 'cubic spline':
        knots = specconf['knots']
        prefix = specconf['prefix']

        curvegen = curvegen_known.CubicSplineCurveGenerator(['C'] + ['C^3'] * (len(knots) - 2),
                                                             depenunit, prefix, knots, csvv)
        minfinder = lambda mintemp, maxtemp: lambda curve: math.minspline.findsplinemin(knots, curve.coeffs, mintemp, maxtemp)
    else:
        user_failure("Unknown functional form %s." % specconf['functionalform'])

    if specconf.get('goodmoney', False):
        baselineloggdppcs = {}
        for region in weatherbundle.regions:
            baselineloggdppcs[region] = covariator.get_current(region)['loggdppc']

    if specconf.get('clipping', False):
        mintemp = specconf.get('clip-mintemp')
        maxtemp = specconf.get('clip-maxtemp')
        # Determine minimum value of curve between 10C and 25C
        baselinecurves, baselinemins = constraints.get_curve_minima(weatherbundle.regions, curvegen, covariator, mintemp, maxtemp,
                                                                    minfinder(mintemp, maxtemp))

    def transform(region, curve):
        final_curve = CoefficientsCurve(curve.ccs, weathernames)

        if specconf.get('clipping', False):
            final_curve = ShiftedCurve(final_curve, -curve(baselinemins[region]))

        if specconf.get('goodmoney', False):
            covars = covariator.get_current(region)
            covars['loggdppc'] = baselineloggdppcs[region]
            noincadapt_unshifted_curve = curvegen.get_curve(region, None, covars, recorddiag=False)
            coeff_noincadapt_unshifted_curve = CoefficientsCurve(noincadapt_unshifted_curve.ccs, weathernames)
            noincadapt_curve = ShiftedCurve(coeff_noincadapt_unshifted_curve, -noincadapt_unshifted_curve(baselinemins[region]))

            final_curve = MinimumCurve(final_curve, noincadapt_curve)

        if specconf.get('goodmoney', False):
            return ClippedCurve(final_curve)
        else:
            return final_curve

    clip_curvegen = curvegen.TransformCurveGenerator(curvegen, transform)
    farm_curvegen = curvegen.FarmerCurveGenerator(clip_curvegen, covariator, farmer)

    calculation = YearlyAverageDay(depenunit, farm_curvegen, specconf['description']),

    return calculation, [], covariator.get_current
