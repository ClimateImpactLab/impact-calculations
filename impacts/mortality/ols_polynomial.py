import csv, copy
import numpy as np
from adaptation import csvvfile, curvegen, curvegen_arbitrary, covariates, constraints
from generate import caller
from openest.models.curve import ZeroInterceptPolynomialCurve
from openest.generate.stdlib import *
from openest.generate import diagnostic
from impactcommon.math import minpoly

def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full'):
    covariator = covariates.CombinedCovariator([covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 15, 2015, varindex=0), {'climtas': 'tas'}),
                                                covariates.EconomicCovariator(economicmodel, 3, 2015)])
    covariator2 = covariates.CombinedCovariator([covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 15, 2015, varindex=0), {'climtas': 'tas'}),
                                                 covariates.EconomicCovariator(economicmodel, 3, 2015)])

    #csvvfile.collapse_bang(csvv, qvals.get_seed())
    
    curr_curvegen = curvegen_arbitrary.CoefficientsCurveGenerator(lambda coeffs: ZeroInterceptPolynomialCurve([-np.inf, np.inf], coeffs),
                                                                  ['C'] * 4, #, 'C^2', 'C^3', 'C^4'],
                                                                  '100,000 * death/population', 'tas', 4, csvv, zerostart=False)
    farm_curvegen = curvegen.FarmerCurveGenerator(curr_curvegen, covariator, farmer)

    # Determine minimum value of curve between 10C and 25C
    print "Determining minimum temperatures."
    with open(caller.callinfo['polyminpath'], 'w') as fp:
        writer = csv.writer(fp)
        writer.writerow(['region', 'brute', 'analytic'])
        baselinemins = {}
        for region in weatherbundle.regions:
            curve = curr_curvegen.get_curve(region, covariator.get_baseline(region))
            temps = np.arange(10, 26)
            mintemp = temps[np.argmin(curve(temps))]
            mintemp2 = minpoly.findpolymin([0] + curve.ccs, 10, 25)
            if np.abs(mintemp - mintemp2) > 1:
                print "WARNING: %s has unclear mintemp: %f, %f" % (region, mintemp, mintemp2)
            baselinemins[region] = np.power(mintemp2, range(1, 5))
            writer.writerow([region, mintemp, mintemp2])
    print "Finishing calculation setup."

    maineffect = YearlyCoefficients('100,000 * death/population', farm_curvegen, "the mortality response curve",
                                    constraints.make_get_coeff_goodmoney(weatherbundle, covariator, curr_curvegen,
                                                                         baselinemins, lambda curve: curve.curr_curve.ccs))

    # Subtract off result at the minimum
    negcsvv = copy.copy(csvv)
    negcsvv['gamma'] = -csvv['gamma']

    negcurr_curvegen = curvegen_arbitrary.CoefficientsCurveGenerator(lambda coeffs: ZeroInterceptPolynomialCurve([-np.inf, np.inf], coeffs),
                                                                     ['C'] * 4, #'C^2', 'C^3', 'C^4'],
                                                                     '100,000 * death/population', 'tas', 4, negcsvv, zerostart=False)
    negfarm_curvegen = curvegen.FarmerCurveGenerator(negcurr_curvegen, covariator2, farmer, save_curve=False)
    baseeffect = YearlyCoefficients('100,000 * death/population', negfarm_curvegen, 'offset to normalize to effect a region minimum',
                                    constraints.make_get_coeff_goodmoney(weatherbundle, covariator, curr_curvegen,
                                                                         baselinemins, lambda curve: curve.curr_curve.ccs, flipsign=True),
                                    weather_change=lambda region, temps: baselinemins[region])

    # Collect all baselines
    calculation = Transform(Positive(Sum([maineffect, baseeffect])),
                            '100,000 * death/population', 'deaths/person/year', lambda x: 365 * x / 1e5,
                            'convert to deaths/person/year', "Divide by 100000 to convert to deaths/person/year.")

    return calculation, [], covariator.get_baseline
