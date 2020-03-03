"""
Compute minutes lost due to temperature effects
"""

import copy
import numpy as np
from openest.generate.stdlib import *
from openest.generate import smart_curve
from adaptation import csvvfile, covariates, constraints, curvegen_known, curvegen
from datastore import modelcache
from climate import discover
from impactlab_tools.utils import files
from impactcommon.math import minpoly

def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full', clipping=True, config={}):
    reader_coldd = discover.discover_yearly_corresponding(files.sharedpath('climate/BCSD/aggregation/cmip5_new/IR_level'),
                                                          weatherbundle.scenario, 'Degreedays_tasmax',
                                                          weatherbundle.model, 'coldd_agg')
    reader_hotdd = discover.discover_yearly_corresponding(files.sharedpath('climate/BCSD/aggregation/cmip5_new/IR_level'),
                                                          weatherbundle.scenario, 'Degreedays_tasmax',
                                                          weatherbundle.model, 'hotdd_agg')
    assert reader_hotdd is not None, "Cannot find corresponding weather to %s, %s, %s, %s" % (weatherbundle.scenario, 'Degreedays_tasmax', weatherbundle.model, 'hotdd_agg')

    variables = ['tasmax'] + ['tasmax%d' % p for p in range(2, 5)]
    
    predgen = covariates.CombinedCovariator([covariates.TranslateCovariator(
        covariates.YearlyWeatherCovariator(reader_hotdd, weatherbundle.regions, 2015, weatherbundle.is_historical(), config=config.get('climcovar', {})),
        {'hotdd_30*(tasmax - 27)*I_{T >= 27}': 'hotdd_agg', 'hotdd_30*(tasmax2 - 27^2)*I_{T >= 27}': 'hotdd_agg',
         'hotdd_30*(tasmax3 - 27^3)*I_{T >= 27}': 'hotdd_agg', 'hotdd_30*(tasmax4 - 27^4)*I_{T >= 27}': 'hotdd_agg'}),
                                             covariates.TranslateCovariator(
        covariates.YearlyWeatherCovariator(reader_coldd, weatherbundle.regions, 2015, weatherbundle.is_historical(), config=config.get('climcovar', {})),
                                                 {'colddd_10*(27 - tasmax)*I_{T < 27}': 'coldd_agg', 'colddd_10*(27^2 - tasmax2)*I_{T < 27}': 'coldd_agg',
                                                  'colddd_10*(27^3 - tasmax3)*I_{T < 27}': 'coldd_agg', 'colddd_10*(27^4 - tasmax4)*I_{T < 27}': 'coldd_agg'},
                                                 {'colddd_10*(27 - tasmax)*I_{T < 27}': lambda x: -x, 'colddd_10*(27^2 - tasmax2)*I_{T < 27}': lambda x: -x,
                                                  'colddd_10*(27^3 - tasmax3)*I_{T < 27}': lambda x: -x, 'colddd_10*(27^4 - tasmax4)*I_{T < 27}': lambda x: -x}),
                                             covariates.EconomicCovariator(economicmodel, 2015, config=config.get('econcovar', {}))])

    csvvfile.collapse_bang(csvv, qvals.get_seed('csvv'))

    order = len(set(csvv['prednames'])) - 1 # -1 because of belowzero
    print("Order", order)

    # We calculate this by splitting the equation into a straight polynomial, and -gamma_H1 27 H - gamma_H2 27^2 H
    def shift_curvegen(poly_curvegen, *covars):
        def shift_curve(region, curve):
            shift = -csvvfile.get_gamma(csvv, 'tasmax', covars[0]) * 27 * predgen.get_current(region)[covars[0]]
            for term in range(2, order+1):
                shift += -csvvfile.get_gamma(csvv, 'tasmax%d' % term, covars[term-1]) * (27**term) * predgen.get_current(region)[covars[term-1]]
            return smart_curve.ShiftedCurve(smart_curve.CoefficientsCurve(curve.ccs, variables[:order]), shift)

        return curvegen.TransformCurveGenerator(shift_curve, "Shift curve by -gamma_H1 27 H - gamma_H2 27^2 H", poly_curvegen)

    lt27_covars = ['colddd_10*(27 - tasmax)*I_{T < 27}'] + ['colddd_10*(27^%d - tasmax%d)*I_{T < 27}' % (term, term) for term in range(2, order+1)]
    lt27_curvegen = shift_curvegen(curvegen_known.PolynomialCurveGenerator(['C'] + ['C^%d' % pow for pow in range(2, order+1)],
                                                                           'minutes worked by individual', 'tasmax', order,
                                                                           csvvfile.filtered(csvv, lambda pred, covar: pred != 'belowzero' and 'I_{T >= 27}' not in covar), diagprefix='lt27-'), *lt27_covars)
    gt27_covars = ['hotdd_30*(tasmax - 27)*I_{T >= 27}'] + ['hotdd_30*(tasmax%d - 27^%d)*I_{T >= 27}' % (term, term) for term in range(2, order+1)]
    gt27_curvegen = shift_curvegen(curvegen_known.PolynomialCurveGenerator(['C'] + ['C^%d' % pow for pow in range(2, order+1)],
                                                                           'minutes worked by individual', 'tasmax', order,
                                                                           csvvfile.filtered(csvv, lambda pred, covar: pred != 'belowzero' and 'I_{T < 27}' not in covar), diagprefix='gt27-'), *gt27_covars)

    def make_piecewise(region, lt27_curve, gt27_curve):
        return smart_curve.PiecewiseCurve([lt27_curve, gt27_curve], [-np.inf, 27, np.inf], lambda ds: ds.tasmax)
    
    piece_curvegen = curvegen.TransformCurveGenerator(make_piecewise, "Piecewise join < 27 and > 27 curves", lt27_curvegen, gt27_curvegen)

    def get_historical_range(key, model, scenario):
        region_mins = {}
        region_maxs = {}
        for region, values in weatherbundle.baseline_values(2015, do_mean=False):
            region_mins[region] = max(5, np.min(values[:, 0]))
            region_maxs[region] = min(30, np.max(values[:, 0]))

        return region_mins, region_maxs
    
    region_mins, region_maxs = modelcache.get_cached_byregion("historical-range", weatherbundle.scenario, weatherbundle.model,
                                                              get_historical_range, {'min': "Historical minimum temperature",
                                                                                     'max': "Historical maximum temperature"}, {})

    def analytic_maximum(region, piecewise_curve):
        mintemp = region_mins[region]
        maxtemp = region_maxs[region]

        if maxtemp < 27:
            return minpoly.findpolymin([0] + [-x for x in piecewise_curve.curves[0].curve.coeffs], mintemp, maxtemp)
        if mintemp > 27:
            return minpoly.findpolymin([0] + [-x for x in piecewise_curve.curves[1].curve.coeffs], mintemp, maxtemp)
        
        maxleft = minpoly.findpolymin([0] + [-x for x in piecewise_curve.curves[0].curve.coeffs], mintemp, 27)
        maxright = minpoly.findpolymin([0] + [-x for x in piecewise_curve.curves[1].curve.coeffs], 27, maxtemp)
        maxvalues = [piecewise_curve(maxleft), piecewise_curve(maxright)]
        if maxvalues[0] <= maxvalues[1]:
            return maxleft
        else:
            return maxright

    baselinecurves, baselinemaxs = constraints.get_curve_minima(weatherbundle.regions, piece_curvegen, predgen,
                                                                region_mins, region_maxs, analytic_maximum)

    def shift_piecewise(region, curve):
        if clipping:
            curve = smart_curve.ClippedCurve(smart_curve.ShiftedCurve(curve, -curve(baselinemaxs[region])), cliplow=False)

        return smart_curve.ProductCurve(smart_curve.ShiftedCurve(curve, -curve(27)), smart_curve.StepCurve([-np.inf, 0, np.inf], [0, 1], lambda ds: ds.tasmax))

    shifted_curvegen = curvegen.TransformCurveGenerator(shift_piecewise, "Subtract curve at 27 C and clip", piece_curvegen) # both clip and subtract curve at 27

    farm_temp_curvegen = curvegen.FarmerCurveGenerator(shifted_curvegen, predgen, farmer)
    tempeffect = YearlyAverageDay('minutes worked by individual', farm_temp_curvegen, 'the temperature effect')

    zerocurvegen = curvegen.ConstantCurveGenerator('C', 'minutes worked by individual', StepCurve([-np.inf, 0, np.inf], [csvv['gamma'][-1], 0], lambda ds: ds.tasmax))
    zeroeffect = YearlyAverageDay('minutes worked by individual', zerocurvegen, "effect from days less than 0 C")

    calculation = Sum([tempeffect, zeroeffect])

    return calculation, [], predgen.get_current
