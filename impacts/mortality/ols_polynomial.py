import csv, copy
import numpy as np
from adaptation import csvvfile, curvegen, curvegen_known, covariates, constraints
from openest.models.curve import ZeroInterceptPolynomialCurve, ClippedCurve, ShiftedCurve, MinimumCurve, OtherClippedCurve, SelectiveInputCurve, CoefficientsCurve
from openest.generate.stdlib import *
from openest.generate import diagnostic
from impactcommon.math import minpoly

def derivative_clipping(ccs, mintemp):
    derivcoeffs = np.array(ccs) * np.arange(1, len(ccs) + 1) # Construct the derivative
    roots = filter(np.isreal, np.roots(derivcoeffs[::-1])) # only consider real roots
    
    deriv2coeffs = derivcoeffs[1:] * np.arange(1, len(derivcoeffs)) # Second derivative
    direction = np.polyval(deriv2coeffs[::-1], roots)
    rootvals = np.polyval(([0] + ccs)[::-1], roots)

    alllimits = set([-np.inf, np.inf])
    levels = [] # min level for each span
    spans = [] # list of tuples with spans
    for ii in range(len(roots)):
        if direction[ii] < 0: # ignore if turning back up
            levels.append(rootvals[ii])
            if roots[ii] < mintemp:
                spans.append((-np.inf, roots[ii]))
                alllimits.update([-np.inf, roots[ii]])
            else:
                spans.append((roots[ii], np.inf))
                alllimits.update([roots[ii], np.inf])
            
    xxlimits = np.sort(list(alllimits))
    yy = []
    for ii in range(len(xxlimits) - 1):
        level = -np.inf
        for jj in range(len(spans)):
            if spans[jj][0] <= xxlimits[ii] and spans[jj][1] >= xxlimits[ii+1]:
                level = max(level, levels[jj])
        yy.append(level)

    return xxlimits, yy

def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full', config={}):
    covariator = covariates.CombinedCovariator([covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 2015, config=config.get('climcovar', {}), varindex=0), {'climtas': 'tas'}),
                                                covariates.EconomicCovariator(economicmodel, 2015, config=config.get('econcovar', {}))])

    # Don't collapse: already collapsed in allmodels
    #csvvfile.collapse_bang(csvv, qvals.get_seed('csvv'))

    order = len(csvv['gamma']) / 3
    curr_curvegen = curvegen_known.PolynomialCurveGenerator(['C'] + ['C^%d' % pow for pow in range(2, order+1)],
                                                           '100,000 * death/population', 'tas', order, csvv)

    if config.get('clipping', 'both') in ['both', 'clip']:
        baselineloggdppcs = {}
        for region in weatherbundle.regions:
            baselineloggdppcs[region] = covariator.get_current(region)['loggdppc']
    
        # Determine minimum value of curve between 10C and 25C
        baselinecurves, baselinemins = constraints.get_curve_minima(weatherbundle.regions, curr_curvegen, covariator, 10, 25,
                                                                    lambda region, curve: minpoly.findpolymin([0] + curve.ccs, 10, 25))

    def transform(region, curve):
        if config.get('clipping', 'both') == 'none':
            return SelectiveInputCurve(CoefficientsCurve(curve.ccs, curve, lambda x: x[:, :order]), range(order))
            
        coeff_curve = SelectiveInputCurve(CoefficientsCurve(curve.ccs, curve, lambda x: x[:, :order]), range(order))

        fulladapt_curve = ShiftedCurve(coeff_curve, -curve(baselinemins[region]))
        if config.get('clipping', 'both') == 'clip':
            # Alternative: Turn off Goodmoney
            return ClippedCurve(fulladapt_curve)

        covars = covariator.get_current(region)
        covars['loggdppc'] = baselineloggdppcs[region]
        noincadapt_unshifted_curve = curr_curvegen.get_curve(region, None, covars, recorddiag=False)
        coeff_noincadapt_unshifted_curve = SelectiveInputCurve(CoefficientsCurve(noincadapt_unshifted_curve.ccs, noincadapt_unshifted_curve, lambda x: x[:, :order]), range(order))
        noincadapt_curve = ShiftedCurve(coeff_noincadapt_unshifted_curve, -noincadapt_unshifted_curve(baselinemins[region]))

        # Alternative: allow no anti-adaptation
        #noincadapt_curve = ShiftedCurve(baselinecurves[region], -baselinecurves[region](baselinemins[region]))

        goodmoney_curve = MinimumCurve(fulladapt_curve, noincadapt_curve)

        if not config.get('derivclip', False):
            return ClippedCurve(goodmoney_curve)

        xxlimits, levels = derivative_clipping(curve.ccs, baselinemins[region])
        return MaximumCurve(ClippedCurve(goodmoney_curve), StepCurve(xxlimits, levels))

    clip_curvegen = curvegen.TransformCurveGenerator(transform, curr_curvegen)
    farm_curvegen = curvegen.FarmerCurveGenerator(clip_curvegen, covariator, farmer)

    # Generate the marginal income curve
    climtas_effect_curve = ZeroInterceptPolynomialCurve([-np.inf, np.inf], 365 * np.array([csvvfile.get_gamma(csvv, tasvar, 'climtas') for tasvar in ['tas', 'tas2', 'tas3', 'tas4', 'tas5'][:order]])) # x 365, to undo / 365 later

    def transform_climtas_effect(region, curve):
        if config.get('clipping', 'both') == 'none':
            return SelectiveInputCurve(CoefficientsCurve(climtas_effect_curve.ccs, climtas_effect_curve, lambda x: x[:, :order]), range(order))
        
        climtas_coeff_curve = SelectiveInputCurve(CoefficientsCurve(climtas_effect_curve.ccs, climtas_effect_curve, lambda x: x[:, :order]), range(order))
        shifted_curve = ShiftedCurve(climtas_coeff_curve, -climtas_effect_curve(baselinemins[region]))

        if not config.get('derivclip', False):
            return OtherClippedCurve(curve, shifted_curve)

        xxlimits, levels = derivative_clipping(curve.ccs, baselinemins[region])
        xxlimits, levels = break_at_crossing(xxlimits, levels)
        return OtherClippedCurve(curve, MinimumCurve(shifted_curve, StepCurve(xxlimits, np.isfinite(levels))))

    climtas_effect_curvegen = curvegen.TransformCurveGenerator(transform_climtas_effect, farm_curvegen)

    # Produce the final calculation
    calculation = Transform(AuxillaryResult(YearlyAverageDay('100,000 * death/population', farm_curvegen,
                                                             "the mortality response curve"),
                                            YearlyAverageDay('100,000 * death/population', climtas_effect_curvegen,
                                                             "climtas effect after clipping", norecord=True), 'climtas_effect'),
                            '100,000 * death/population', 'deaths/person/year', lambda x: 365 * x / 1e5,
                            'convert to deaths/person/year', "Divide by 100000 to convert to deaths/person/year.")

    return calculation, [], covariator.get_current

if __name__ == '__main__':
    print derivative_clipping([12, -2, -4, 1], 0) # W-curve
    print derivative_clipping([-2, -12, 2, 1], 2) # W-curve, but only a problem to left
    print derivative_clipping([-36, 42, -20, 3], 3) # U all above 0
    print derivative_clipping([22, 6, -2, 1], 0) # U sloping down at min
