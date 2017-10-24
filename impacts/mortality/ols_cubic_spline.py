import numpy as np
from adaptation import csvvfile, curvegen, curvegen_known, covariates, constraints
from openest.generate.smart_curve import SelectiveInputCurve
from openest.models.curve import CubicSplineCurve, ClippedCurve, ShiftedCurve, MinimumCurve, OtherClippedCurve
from openest.generate.stdlib import *
from impactcommon.math import minspline

knots = [-10, 0, 10, 20, 28, 33]

def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full', config={}):
    covariator = covariates.CombinedCovariator([covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 2015, 'tas', config=config.get('climcovar', {}), varindex=0), {'climtas': 'tas'}),
                                                covariates.EconomicCovariator(economicmodel, 2015, config=config.get('econcovar', {}))])

    # Don't collapse: already collapsed in allmodels
    #csvvfile.collapse_bang(csvv, qvals.get_seed())

    curr_curvegen = curvegen_known.CubicSplineCurveGenerator(['C'] + ['C^3'] * (len(knots) - 2),
                                                             '100,000 * death/population', 'spline_variables-',
                                                             knots, csvv)

    baselineloggdppcs = {}
    for region in weatherbundle.regions:
        baselineloggdppcs[region] = covariator.get_current(region)['loggdppc']

    # Determine minimum value of curve between 10C and 25C
    baselinecurves, baselinemins = constraints.get_curve_minima(weatherbundle.regions, curr_curvegen, covariator, 10, 25,
                                                                lambda region, curve: minspline.findsplinemin(knots, curve.coeffs, 10, 25))

    def transform(region, curve):
        fulladapt_curve = ShiftedCurve(SelectiveInputCurve(curve, 'tas'), -curve(baselinemins[region]))
        # Alternative: Turn off Goodmoney
        #return ClippedCurve(fulladapt_curve)

        covars = covariator.get_current(region)
        covars['loggdppc'] = baselineloggdppcs[region]
        noincadapt_unshifted_curve = curr_curvegen.get_curve(region, None, covars, recorddiag=False)
        noincadapt_curve = ShiftedCurve(SelectiveInputCurve(noincadapt_unshifted_curve, 'tas'), -noincadapt_unshifted_curve(baselinemins[region]))

        # Alternative: allow no anti-adaptation
        #noincadapt_curve = ShiftedCurve(baselinecurves[region], -baselinecurves[region](baselinemins[region]))

        goodmoney_curve = MinimumCurve(fulladapt_curve, noincadapt_curve)
        return ClippedCurve(goodmoney_curve)

    clip_curvegen = curvegen.TransformCurveGenerator(transform, "Clipping and Good Money", curr_curvegen)
    farm_curvegen = curvegen.FarmerCurveGenerator(clip_curvegen, covariator, farmer)

    # Generate the marginal income curve
    climtas_effect_curve = CubicSplineCurve(knots, 365 * np.array([csvvfile.get_gamma(csvv, tasvar, 'climtas') for tasvar in ['spline_variables-0', 'spline_variables-1', 'spline_variables-2', 'spline_variables-3', 'spline_variables-4']])) # x 365, to undo / 365 later

    def transform_climtas_effect(region, curve):
        climtas_coeff_curve = SelectiveInputCurve(climtas_effect_curve, 'tas')
        shifted_curve = ShiftedCurve(climtas_coeff_curve, -climtas_effect_curve(baselinemins[region]))
        return OtherClippedCurve(curve, shifted_curve)

    climtas_effect_curvegen = curvegen.TransformCurveGenerator(transform_climtas_effect, "Calculate climtas partial equation", farm_curvegen)

    calculation = Transform(AuxillaryResult(YearlyAverageDay('100,000 * death/population', farm_curvegen, "the mortality response curve"),
                                            YearlyAverageDay('100,000 * death/population', climtas_effect_curvegen,
                                                             "climtas effect after clipping", norecord=True), 'climtas_effect'),
                            '100,000 * death/population', 'deaths/person/year', lambda x: 365 * x / 1e5,
                            'convert to deaths/person/year', "Divide by 100000 to convert to deaths/person/year.")

    return calculation, [], covariator.get_current
