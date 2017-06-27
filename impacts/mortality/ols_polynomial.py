import csv, copy
import numpy as np
from adaptation import csvvfile, curvegen, curvegen_known, covariates, constraints
from openest.models.curve import ZeroInterceptPolynomialCurve, ClippedCurve, ShiftedCurve, MinimumCurve, SelectiveZeroCurve
from openest.generate.stdlib import *
from openest.generate import diagnostic
from impactcommon.math import minpoly

## NOTE: Currently allows no anti-adaptation, because constantcurves don't respond to temp;
##  Problem is that full curve gets regenerated, but not constantcurves.

def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full'):
    covariator = covariates.CombinedCovariator([covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 15, 2015), {'climtas': 'tas'}),
                                                covariates.EconomicCovariator(economicmodel, 3, 2015)])

    # Don't collapse: already collapsed in allmodels
    #csvvfile.collapse_bang(csvv, qvals.get_seed())

    order = len(csvv['gamma']) / 3
    curr_curvegen = curvegen_known.PolynomialCurveGenerator(['C'] + ['C^%d' % pow for pow in range(2, order+1)],
                                                           '100,000 * death/population', 'tas', order, csvv)

    # Determine minimum value of curve between 10C and 25C
    baselinecurves, baselinemins = constraints.get_curve_minima(weatherbundle, curr_curvegen, covariator, 10, 25,
                                                                lambda curve: minpoly.findpolymin([0] + curve.ccs, 10, 25))

    def transform(region, curve):
        fulladapt_curve = ShiftedCurve(curve, -curve(baselinemins[region]))
        #return ClippedCurve(fulladapt_curve) # XXX: Turn off Goodmoney
        
        noincadapt_curve = ShiftedCurve(baselinecurves[region], -baselinecurves[region](baselinemins[region]))

        goodmoney_curve = MinimumCurve(fulladapt_curve, noincadapt_curve)
        return ClippedCurve(goodmoney_curve)

    clip_curvegen = curvegen.TransformCurveGenerator(curr_curvegen, transform)
    farm_curvegen = curvegen.FarmerCurveGenerator(clip_curvegen, covariator, farmer)

    # Generate the marginal income curve
    climtas_effect_curve = ZeroInterceptPolynomialCurve([-np.inf, np.inf], 365 * [csvvfile.get_gamma(csvv, tasvar, 'climtas') for tasvar in ['tas', 'tas2', 'tas3', 'tas4', 'tas5'][:order]]) # x 365, to undo / 365 later

    def transform_climtas_effect(region, curve):
        assert isinstance(curve, ClippedCurve)
        shifted_curve = ShiftedCurve(climtas_effect_curve, -climtas_effect_curve(baselinemins[region]))
        if region == 'IND.10.121.371':
            print np.mean(curve.last_clipped) if curve.last_clipped is not None else "Pre-clipping."
            print curve.last_clipped
        return SelectiveZeroCurve(shifted_curve, curve.last_clipped)

    climtas_effect_curvegen = curvegen.TransformCurveGenerator(farm_curvegen, transform_climtas_effect)

    # Produce the final calculation
    calculation = Transform(AuxillaryResult(YearlyAverageDay('100,000 * death/population', farm_curvegen,
                                                             "the mortality response curve"),
                                            YearlyAverageDay('100,000 * death/population', climtas_effect_curvegen,
                                                             "climtas effect after clipping", norecord=True), 'climtas_effect'),
                            '100,000 * death/population', 'deaths/person/year', lambda x: 365 * x / 1e5,
                            'convert to deaths/person/year', "Divide by 100000 to convert to deaths/person/year.")

    return calculation, [], covariator.get_current
