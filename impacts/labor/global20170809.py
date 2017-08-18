"""
Compute minutes lost due to temperature effects
"""

import copy
import numpy as np
from openest.generate.stdlib import *
from openest.models.curve import FlatCurve, ShiftedCurve, PiecewiseCurve, ClippedCurve, ProductCurve, CoefficientsCurve
from adaptation import csvvfile, covariates, constraints, curvegen_known, curvegen
from datastore import modelcache
from climate import discover
from impactlab_tools.utils import files
from impactcommon.math import minpoly

def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full', clipping=True):
    reader_coldd = discover.discover_yearly_corresponding(files.sharedpath('climate/BCSD/aggregation/cmip5_new/IR_level'),
                                                          weatherbundle.scenario, 'Degreedays_tasmax',
                                                          weatherbundle.model, 'coldd_agg')
    reader_hotdd = discover.discover_yearly_corresponding(files.sharedpath('climate/BCSD/aggregation/cmip5_new/IR_level'),
                                                          weatherbundle.scenario, 'Degreedays_tasmax',
                                                          weatherbundle.model, 'hotdd_agg')

    predgen = covariates.CombinedCovariator([covariates.TranslateCovariator(
        covariates.YearlyWeatherCovariator(reader_hotdd, weatherbundle.regions, 2015, 15, weatherbundle.is_historical()),
        {'hotdd_30*(tasmax - 27)*I_{T >= 27}': 'hotdd_agg', 'hotdd_30*(tasmax2 - 27^2)*I_{T >= 27}': 'hotdd_agg'}),
                                             covariates.TranslateCovariator(
        covariates.YearlyWeatherCovariator(reader_coldd, weatherbundle.regions, 2015, 15, weatherbundle.is_historical()),
                                                 {'colddd_10*(27 - tasmax)*I_{T < 27}': 'coldd_agg', 'colddd_10*(27^2 - tasmax2)*I_{T < 27}': 'coldd_agg'},
                                                 {'colddd_10*(27 - tasmax)*I_{T < 27}': lambda x: -x, 'colddd_10*(27^2 - tasmax2)*I_{T < 27}': lambda x: -x}),
                                             covariates.EconomicCovariator(economicmodel, 1, 2015)])

    csvvfile.collapse_bang(csvv, qvals.get_seed())

    order = len(set(csvv['prednames'])) - 1 # -1 because of belowzero
    print "Order", order

    # We calculate this by splitting the equation into a straight polynomial, and -gamma_H1 27 H - gamma_H2 27^2 H
    def shift_curvegen(poly_curvegen, covar1, covar2):
        def shift_curve(region, curve):
            shift1 = -csvvfile.get_gamma(csvv, 'tasmax', covar1) * 27 * predgen.get_current(region)[covar1]
            shift2 = -csvvfile.get_gamma(csvv, 'tasmax2', covar2) * 27*27 * predgen.get_current(region)[covar2]
            return ShiftedCurve(CoefficientsCurve(curve.ccs, curve, lambda x: x[:, :order]), shift1 + shift2)

        return curvegen.TransformCurveGenerator(shift_curve, poly_curvegen)

    lt27_curvegen = shift_curvegen(curvegen_known.PolynomialCurveGenerator(['C'] + ['C^%d' % pow for pow in range(2, order+1)],
                                                                           'minutes worked by individual', 'tasmax', order,
                                                                           csvvfile.filtered(csvv, lambda pred, covar: pred != 'belowzero' and 'I_{T >= 27}' not in covar), diagsuffix='lt27-'), 'colddd_10*(27 - tasmax)*I_{T < 27}', 'colddd_10*(27^2 - tasmax2)*I_{T < 27}')
    gt27_curvegen = shift_curvegen(curvegen_known.PolynomialCurveGenerator(['C'] + ['C^%d' % pow for pow in range(2, order+1)],
                                                                           'minutes worked by individual', 'tasmax', order,
                                                                           csvvfile.filtered(csvv, lambda pred, covar: pred != 'belowzero' and 'I_{T < 27}' not in covar), diagsuffix='gt27-'), 'hotdd_30*(tasmax - 27)*I_{T >= 27}', 'hotdd_30*(tasmax2 - 27^2)*I_{T >= 27}')

    def make_piecewise(region, lt27_curve, gt27_curve):
        return PiecewiseCurve([lt27_curve, gt27_curve], [-np.inf, 27, np.inf], lambda x: x[:, 0])
    
    piece_curvegen = curvegen.TransformCurveGenerator(make_piecewise, lt27_curvegen, gt27_curvegen)

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

    def analytic_minimum(region, piecewise_curve):
        mintemp = region_mins[region]
        maxtemp = region_maxs[region]

        if maxtemp < 27:
            return minpoly.findpolymin([0] + piecewise_curve.curves[0].curve.coeffs, mintemp, maxtemp)
        if mintemp > 27:
            return minpoly.findpolymin([0] + piecewise_curve.curves[1].curve.coeffs, mintemp, maxtemp)
        
        minleft = minpoly.findpolymin([0] + piecewise_curve.curves[0].curve.coeffs, mintemp, 27)
        minright = minpoly.findpolymin([0] + piecewise_curve.curves[1].curve.coeffs, 27, maxtemp)
        minvalues = [piecewise_curve(minleft), piecewise_curve(minright)]
        if minvalues[0] <= minvalues[1]:
            return minleft
        else:
            return minright

    baselinecurves, baselinemins = constraints.get_curve_minima(weatherbundle.regions, piece_curvegen, predgen,
                                                                region_mins, region_maxs, analytic_minimum)

    def shift_piecewise(region, curve):
        if clipping:
            curve = ClippedCurve(ShiftedCurve(curve, -curve(baselinemins[region])))

        return ProductCurve(ShiftedCurve(curve, -curve(27)), StepCurve([-np.inf, 0, np.inf], [0, 1], lambda x: x[:, 0]))

    shifted_curvegen = curvegen.TransformCurveGenerator(shift_piecewise, piece_curvegen) # both clip and subtract curve at 27

    farm_temp_curvegen = curvegen.FarmerCurveGenerator(shifted_curvegen, predgen, farmer)
    tempeffect = YearlyAverageDay('minutes worked by individual', farm_temp_curvegen, 'the temperature effect')

    zerocurvegen = curvegen.ConstantCurveGenerator('C', 'minutes worked by individual', FlatCurve(csvv['gamma'][-1]))
    zeroeffect = YearlyAverageDay('minutes worked by individual', zerocurvegen, "effect from days less than 0 C", weather_change=lambda region, temps: temps[:, 0] < 0)

    calculation = Sum([tempeffect, zeroeffect])

    return calculation, [], predgen.get_current
