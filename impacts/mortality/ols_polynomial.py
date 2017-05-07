import csv, copy
import numpy as np
from adaptation import csvvfile, curvegen, curvegen_poly, covariates, constraints
from generate import caller
from openest.models.curve import ZeroInterceptPolynomialCurve, ClippedCurve, ShiftedCurve, MinimumCurve
from openest.generate.stdlib import *
from openest.generate import diagnostic
from impactcommon.math import minpoly

def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full'):
    covariator = covariates.CombinedCovariator([covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 15, 2015), {'climtas': 'tas'}),
                                                covariates.EconomicCovariator(economicmodel, 3, 2015)])
    covariator2 = covariates.CombinedCovariator([covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 15, 2015), {'climtas': 'tas'}),
                                                covariates.EconomicCovariator(economicmodel, 3, 2015)])

    # Don't collapse: already collapsed in allmodels
    #csvvfile.collapse_bang(csvv, qvals.get_seed())

    curr_curvegen = curvegen_poly.PolynomialCurveGenerator(['C'] * 4, #, 'C^2', 'C^3', 'C^4'],
                                                           '100,000 * death/population', 'tas', 4, csvv)

    # Determine minimum value of curve between 10C and 25C
    print "Determining minimum temperatures."
    baselinemins = {}
    constantincomecurves = {}
    with open(caller.callinfo['polyminpath'], 'w') as fp:
        writer = csv.writer(fp)
        writer.writerow(['region', 'brute', 'analytic'])
        for region in weatherbundle.regions:
            curve = curr_curvegen.get_curve(region, covariator.get_current(region))
            temps = np.arange(10, 26)
            mintemp = temps[np.argmin(curve(temps))]
            mintemp2 = minpoly.findpolymin([0] + curve.ccs, 10, 25)
            if np.abs(mintemp - mintemp2) > 1:
                print "WARNING: %s has unclear mintemp: %f, %f" % (region, mintemp, mintemp2)
            baselinemins[region] = mintemp2
            writer.writerow([region, mintemp, mintemp2])

            constantincomecurves[region] = constraints.ConstantIncomeInstantAdaptingCurve(region, curr_curvegen.get_curve(region, covariator.get_current(region)), covariator2, curr_curvegen)
    print "Finishing calculation setup."
    
    def transform(region, curve):
        goodmoney_curve = MinimumCurve(curve, constantincomecurves[region])
        return ClippedCurve(ShiftedCurve(goodmoney_curve, -curve(baselinemins[region])))

    clip_curvegen = curvegen.TransformCurveGenerator(curr_curvegen, transform)
    farm_curvegen = curvegen.FarmerCurveGenerator(clip_curvegen, covariator, farmer)

    calculation = Transform(YearlyAverageDay('100,000 * death/population', farm_curvegen, "the mortality response curve"),
                            '100,000 * death/population', 'deaths/person/year', lambda x: 365 * x / 1e5,
                            'convert to deaths/person/year', "Divide by 100000 to convert to deaths/person/year.")

    return calculation, [], covariator.get_current
