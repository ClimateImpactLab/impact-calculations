import csv, copy
import numpy as np
from adaptation import csvvfile, curvegen, curvegen_known, covariates, constraints
from interpret import configs
from openest.models.curve import ZeroInterceptPolynomialCurve, ClippedCurve, ShiftedCurve, MinimumCurve, OtherClippedCurve, SelectiveInputCurve, CoefficientsCurve, ProductCurve
from openest.generate.stdlib import *
from openest.generate import diagnostic
from impactcommon.math import minpoly

class UShapedCurve(UnivariateCurve):
    def __init__(self, curve, mintemp, gettas):
        super(UShapedCurve, self).__init__(curve.xx)
        self.curve = curve
        self.mintemp = mintemp
        self.gettas = gettas

    def __call__(self, xs):
        values = self.curve(xs)
        tas = self.gettas(xs)
        order = np.argsort(tas)
        orderedtas = tas[order]
        orderedvalues = values[order]

        lowvalues = orderedvalues[orderedtas < self.mintemp]
        lowvalues2 = np.maximum.accumulate(lowvalues[::-1])

        highvalues = orderedvalues[orderedtas >= self.mintemp]
        highvalues2 = np.maximum.accumulate(highvalues)

        return np.concatenate((lowvalues2, highvalues2))

# Return tmarginal evaluated at the innermost edge of plateaus
class UShapedClipping(UnivariateCurve):
    def __init__(self, curve, tmarginal_curve, mintemp, gettas):
        super(UShapedClipping, self).__init__(curve.xx)
        self.curve = curve
        self.tmarginal_curve = tmarginal_curve
        self.mintemp = mintemp
        self.gettas = gettas

    def __call__(self, xs):
        increasingvalues = self.curve(xs) # these are ordered as low..., high...
        increasingplateaus = np.diff(increasingvalues) == 0

        tas = self.gettas(xs)
        order = np.argsort(tas)
        orderedtas = tas[order]

        n_below = sum(orderedtas < self.mintemp)
        
        lowindicesofordered = np.arange(n_below)[::-1] # [N-1 ... 0]
        if len(lowindicesofordered) > 1:
            lowindicesofordered[np.concatenate(([False], increasingplateaus[:len(lowindicesofordered)-1]))] = n_below
            lowindicesofordered = np.minimum.accumulate(lowindicesofordered)
        
        highindicesofordered = np.arange(sum(orderedtas >= self.mintemp)) + n_below # [N ... T-1]
        if len(highindicesofordered) > 1:
            highindicesofordered[np.concatenate(([False], increasingplateaus[-len(highindicesofordered)+1:]))] = n_below
            highindicesofordered = np.maximum.accumulate(highindicesofordered)

        increasingresults = np.concatenate((self.tmarginal_curve(xs[order[lowindicesofordered], :]), self.tmarginal_curve(xs[order[highindicesofordered], :]))) # ordered low..., high...
        increasingresults[increasingvalues <= 0] = 0 # replace truly clipped with 0

        return increasingresults
    
def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full', config={}):
    covariator = covariates.CombinedCovariator([covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 2015, config=configs.merge(config, 'climcovar'), varindex=0), {'climtas': 'tas'}),
                                                covariates.EconomicCovariator(economicmodel, 2015, config=configs.merge(config, 'econcovar'))])

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
        baselinecurves, baselinemins = constraints.get_curve_minima(weatherbundle.regions, curr_curvegen, covariator, config.get('clip-mintemp', 10), config.get('clip-maxtemp', 25),
                                                                    lambda region, curve: minpoly.findpolymin([0] + curve.ccs, config.get('clip-mintemp', 10), config.get('clip-maxtemp', 25)))

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

        return UShapedCurve(ClippedCurve(goodmoney_curve), baselinemins[region], lambda xs: xs[:, 0])

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

        return UShapedClipping(curve, shifted_curve, baselinemins[region], lambda xs: xs[:, 0])

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
    curve = ZeroInterceptPolynomialCurve([-np.inf, np.inf], [-2, -12, 2, 1])
    ucurve = UShapedCurve(curve, -1, lambda x: x)

    xx = np.arange(-6, 4)
    print xx
    print curve(xx)
    print ucurve(xx)
    
