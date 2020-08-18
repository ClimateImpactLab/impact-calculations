import csv, copy
from datetime import date
import numpy as np
from adaptation import csvvfile, curvegen, curvegen_known, covariates, constraints
from interpret import configs
from openest.generate.smart_curve import ZeroInterceptPolynomialCurve, ClippedCurve, ShiftedCurve, MinimumCurve, OtherClippedCurve, SelectiveInputCurve, CoefficientsCurve, ProductCurve
from openest.generate.stdlib import *
from openest.generate import diagnostic
from openest.curves import ushape_numeric
from impactcommon.math import minpoly

def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full', config=None):
    if config is None:
        config = {}
    covariator = covariates.CombinedCovariator([covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, config.get('endbaseline', 2015), config=configs.merge(config, 'climcovar'), variable='tas'), {'climtas': 'tas'}),
                                                covariates.EconomicCovariator(economicmodel, config.get('endbaseline', 2015), config=configs.merge(config, 'econcovar'))])

    # Don't collapse: already collapsed in allmodels
    #csvvfile.collapse_bang(csvv, qvals.get_seed('csvv'))

    order = int(len(csvv['gamma']) / 3)
    weathernames = ['tas', 'tas-poly-2', 'tas-poly-3', 'tas-poly-4', 'tas-poly-5'][:order]
    curr_curvegen = curvegen_known.PolynomialCurveGenerator(['C'] + ['C^%d' % pow for pow in range(2, order+1)],
                                                            '100,000 * death/population', 'tas', order, csvv,
                                                            weathernames=weathernames)
    
    if config.get('clipping', 'both') in ['both', 'clip']:
        baselineloggdppcs = {}
        for region in weatherbundle.regions:
            baselineloggdppcs[region] = covariator.get_current(region)['loggdppc']
    
        # Determine minimum value of curve between 10C and 25C
        baselinecurves, baselinemins = constraints.get_curve_minima(weatherbundle.regions, curr_curvegen, covariator, config.get('clip-mintemp', 10), config.get('clip-maxtemp', 25),
                                                                    lambda region, curve: minpoly.findpolymin([0] + curve.coeffs, config.get('clip-mintemp', 10), config.get('clip-maxtemp', 25)))

        fillins = np.arange(-40, 50, 1.)

    def transform(region, curve):
        coeff_curve = CoefficientsCurve(curve.coeffs, weathernames)
        if config.get('clipping', 'both') == 'none':
            return coeff_curve

        fulladapt_curve = ShiftedCurve(coeff_curve, -curve.univariate(baselinemins[region]))
        if config.get('clipping', 'both') == 'clip':
            # Alternative: Turn off Goodmoney
            return ClippedCurve(fulladapt_curve)

        covars = covariator.get_current(region)
        covars['loggdppc'] = baselineloggdppcs[region]
        noincadapt_unshifted_curve = curr_curvegen.get_curve(region, None, covars, recorddiag=False)
        coeff_noincadapt_unshifted_curve = CoefficientsCurve(noincadapt_unshifted_curve.coeffs, weathernames)
        noincadapt_curve = ShiftedCurve(coeff_noincadapt_unshifted_curve, -noincadapt_unshifted_curve.univariate(baselinemins[region]))

        # Alternative: allow no anti-adaptation
        #noincadapt_curve = ShiftedCurve(baselinecurves[region], -baselinecurves[region](baselinemins[region]))

        goodmoney_curve = MinimumCurve(fulladapt_curve, noincadapt_curve)

        if not config.get('derivclip', False):
            return ClippedCurve(goodmoney_curve)

        unicurve = MinimumCurve(ShiftedCurve(curve, -curve.univariate(baselinemins[region])), ShiftedCurve(noincadapt_unshifted_curve, -noincadapt_unshifted_curve.univariate(baselinemins[region])))
        return ushape_numeric.UShapedCurve(ClippedCurve(goodmoney_curve), baselinemins[region], lambda ds: ds['tas']._data, fillxxs=fillins, fillyys=unicurve.univariate(fillins))

    clip_curvegen = curvegen.TransformCurveGenerator(transform, "Clipping and Good Money", curr_curvegen)
    farm_curvegen = curvegen.FarmerCurveGenerator(clip_curvegen, covariator, farmer, endbaseline=config.get('endbaseline', 2015))

    # Generate the marginal income curve
    climtas_effect_curve = ZeroInterceptPolynomialCurve(365 * np.array([csvvfile.get_gamma(csvv, tasvar, 'climtas') for tasvar in ['tas', 'tas2', 'tas3', 'tas4', 'tas5'][:order]]), weathernames) # x 365, to undo / 365 later

    def transform_climtas_effect(region, curve):
        climtas_coeff_curve = CoefficientsCurve(climtas_effect_curve.coeffs, weathernames)
        if config.get('clipping', 'both') == 'none':
            return climtas_coeff_curve

        shifted_curve = ShiftedCurve(climtas_coeff_curve, -climtas_effect_curve.univariate(baselinemins[region]))

        if not config.get('derivclip', False):
            return OtherClippedCurve(curve, shifted_curve)

        return ushape_numeric.UShapedClipping(curve, shifted_curve, baselinemins[region], lambda ds: ds['tas']._data)

    climtas_effect_curvegen = curvegen.TransformCurveGenerator(transform_climtas_effect, "Calculate climtas partial equation", farm_curvegen)

    # Produce the final calculation

    if config.get('filter') == 'jun-aug':
        def weather_change(region, x):
            x2 = np.copy(x)
            # 1950 is a non-leap year
            x2[0:(date(1950, 6, 1) - date(1950, 1, 1)).days] = np.nan
            x2[(date(1950, 9, 1) - date(1950, 1, 1)).days:] = np.nan
            return x2
    else:
        weather_change = lambda region, x: x
        
    calculation = Transform(AuxillaryResult(YearlyAverageDay('100,000 * death/population', farm_curvegen,
                                                             "the mortality response curve",
                                                             weather_change),
                                            YearlyAverageDay('100,000 * death/population', climtas_effect_curvegen,
                                                             "climtas effect after clipping", norecord=True), 'climtas_effect'),
                            '100,000 * death/population', 'deaths/person/year', lambda x: 365 * x / 1e5,
                            'convert to deaths/person/year', "Divide by 100000 to convert to deaths/person/year.")

    return calculation, [], covariator.get_current
