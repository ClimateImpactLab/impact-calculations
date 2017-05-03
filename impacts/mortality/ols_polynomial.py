import numpy as np
from adaptation import csvvfile, curvegen, curvegen_arbitrary, covariates
from generate import caller
from openest.generate.stdlib import *
from openest.generate import diagnostic
import csv, copy

def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full'):
    covariator = covariates.CombinedCovariator([covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 15, 2015, varindex=0), {'climtas': 'tas'}),
                                                covariates.EconomicCovariator(economicmodel, 3, 2015)])
    covariator2 = covariates.CombinedCovariator([covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 15, 2015, varindex=0), {'climtas': 'tas'}),
                                                 covariates.EconomicCovariator(economicmodel, 3, 2015)])

    #csvvfile.collapse_bang(csvv, qvals.get_seed())
    ## CONTINUE FROM HERE
    
    curr_curvegen = curvegen_arbitrary.CoefficientsCurveGenerator(lambda coeffs: CubicSplineCurve(knots, coeffs),
                                                        ['C'] + ['C^3'] * (len(knots) - 2),
                                                        '100,000 * death/population', 'spline_variables-', len(knots) - 1, csvv)
    farm_curvegen = curvegen.FarmerCurveGenerator(curr_curvegen, covariator, farmer)

    # Determine minimum value of curve between 10C and 25C
    print "Determining minimum temperatures."
    with open(caller.callinfo['splineminpath'], 'w') as fp:
        writer = csv.writer(fp)
        writer.writerow(['region', 'brute', 'analytic'])
        baselinemins = {}
        for region in weatherbundle.regions:
            curve = curr_curvegen.get_curve(region, covariator.get_baseline(region))
            temps = np.arange(10, 26)
            mintemp = temps[np.argmin(curve(temps))]
            mintemp2 = minspline.findsplinemin(knots, curve.coeffs, 10, 25)
            if np.abs(mintemp - mintemp2) > 1:
                print "WARNING: %s has unclear mintemp: %f, %f" % (region, mintemp, mintemp2)
            baselinemins[region] = mintemp2
            writer.writerow([region, mintemp, mintemp2])
    print "Finishing calculation setup."

    # Generating all curves, for baseline
    baseline_loggdppc = {}
    for region in weatherbundle.regions:
        baseline_loggdppc[region] = covariator.get_baseline(region)['loggdppc']

    loggdppc_marginals = curr_curvegen.get_marginals('loggdppc')
    loggdppc_marginals = np.array([loggdppc_marginals[predname] for predname in curr_curvegen.prednames]) # same order as temps
    print "MARGINALS"
    print loggdppc_marginals

    def coeff_getter_positive(region, year, temps, curve):
        mareff = np.sum(loggdppc_marginals * (temps - 365 * np.array(CubicSplineCurve(knots, None).get_terms(baselinemins[region]))))
        if mareff > 0:
            deltaloggdppc = covariator.get_baseline(region)['loggdppc'] - baseline_loggdppc[region] # get_baseline gives current sense, not really baseline
            return curve.curr_curve.coeffs - deltaloggdppc * loggdppc_marginals
        else:
            return curve.curr_curve.coeffs

    def coeff_getter_negative(region, year, temps, curve):
        mareff = np.sum(loggdppc_marginals * (temps - 365 * np.array(CubicSplineCurve(knots, None).get_terms(baselinemins[region]))))
        if mareff > 0:
            deltaloggdppc = covariator.get_baseline(region)['loggdppc'] - baseline_loggdppc[region] # get_baseline gives current sense, not really baseline
            return curve.curr_curve.coeffs + deltaloggdppc * loggdppc_marginals
        else:
            return curve.curr_curve.coeffs

    maineffect = YearlyCoefficients('100,000 * death/population', farm_curvegen, "the mortality response curve", coeff_getter_positive)

    # Subtract off result at 20C; currently need to reproduce adapting curve
    negcsvv = copy.copy(csvv)
    negcsvv['gamma'] = -csvv['gamma']

    negcurr_curvegen = curvegen_arbitrary.CoefficientsCurveGenerator(lambda coeffs: CubicSplineCurve(knots, coeffs),
                                                                     ['C'] + ['C^3'] * (len(knots) - 2),
                                                                     '100,000 * death/population', 'spline_variables-', len(knots) - 1, negcsvv)
    negfarm_curvegen = curvegen.FarmerCurveGenerator(negcurr_curvegen, covariator2, farmer, save_curve=False)
    baseeffect = YearlyCoefficients('100,000 * death/population', negfarm_curvegen, 'offset to normalize to 20 C', coeff_getter_negative, weather_change=lambda region, temps: 365 * np.array(CubicSplineCurve(knots, np.zeros(len(knots)-1)).get_terms(baselinemins[region])))

    # Collect all baselines
    calculation = Transform(Positive(Sum([maineffect, baseeffect])),
                            '100,000 * death/population', 'deaths/person/year', lambda x: x / 1e5,
                            'convert to deaths/person/year', "Divide by 100000 to convert to deaths/person/year.")

    return calculation, [], covariator.get_baseline
