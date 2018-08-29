import re
import numpy as np
from adaptation import csvvfile, curvegen, curvegen_arbitrary, covariates
from openest.models.curve import StepCurve, OtherClippedCurve, CoefficientsCurve
from openest.generate.stdlib import *

def prepare_interp_raw(csvv, weatherbundle, economicmodel, pvals, farmer='full', config={}):
    covariator = covariates.CombinedCovariator([covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 2015, config=config.get('climcovar', {}), varindex=0), {'climtas': 'tas'}),
                                                covariates.EconomicCovariator(economicmodel, 2015, config=config.get('econcovar', {}))])

    curr_curvegen = curvegen_arbitrary.CoefficientsCurveGenerator(curvegen_arbitrary.ParameterHolderCurve, map(lambda label: config['terms'][label]['unit'], config['terms']), '100,000 * death/population', map(lambda label: config['terms'][label]['coeffvar'], config['terms']), csvv)

    terms = config['terms'].values()

    if config.get('clipping', 'both') == 'both':
        baselineloggdppcs = {}
        for region in weatherbundle.regions:
            baselineloggdppcs[region] = covariator.get_current(region)['loggdppc']
    
    def clip_transform(region, curve):
        if config.get('clipping', 'both') == 'none':
            coeffs = curve.params
        else:
            coeffs = map(lambda coeff: max(coeff, 0), curve.params)

            if config.get('clipping', 'both') == 'both':
                covars = covariator.get_current(region)
                covars['loggdppc'] = baselineloggdppcs[region]
                noincadapt_curve = curr_curvegen.get_curve(region, None, covars)

                coeffs = [min(coeffs[ii], max(noincadapt_curve.params[ii], 0)) for ii in range(len(coeffs))]
            
        return CoefficientsCurve(coeffs, lambda x: np.nan)

    def clip_transform_climtas(region, curve):
        coeffs = map(lambda kk: csvvfile.get_gamma(csvv, terms[kk]['coeffvar'], 'climtas') if curve.coeffs[kk] > 0 else 0, range(len(curve.coeffs)))
        return CoefficientsCurve(coeffs, lambda x: np.nan)

    clip_curvegen = curvegen.TransformCurveGenerator(clip_transform, curr_curvegen)
    farm_curvegen = curvegen.FarmerCurveGenerator(clip_curvegen, covariator, farmer)
    climtas_curvegen = curvegen.TransformCurveGenerator(clip_transform_climtas, farm_curvegen)

    getters = [lambda region, year, temps, curve: curve.coeffs[0], lambda region, year, temps, curve: curve.coeffs[1], lambda region, year, temps, curve: curve.coeffs[2], lambda region, year, temps, curve: curve.coeffs[3]]
    changers = [lambda region, x: x[1], lambda region, x: x[2], lambda region, x: x[3], lambda region, x: x[4]] # start with 1, so not use tas
    
    main_calcs = []
    climtas_calcs = []
    for kk in range(len(terms)):
        
        main_calc = YearlyCoefficients('100,000 * death/population', farm_curvegen, terms[kk]['description'],
                                       getter=getters[kk], weather_change=changers[kk], label=config['terms'].keys()[kk])
        climtas_calc = YearlyCoefficients('100,000 * death/population', climtas_curvegen, "climtas effect for %s" % terms[kk]['description'],
                                          getter=getters[kk], weather_change=changers[kk], label=config['terms'].keys()[kk] + '_climtas')

        main_calcs.append(main_calc)
        climtas_calcs.append(climtas_calc)

    # Collect all baselines
    calculation = Transform(
        AuxillaryResult(
            Sum(main_calcs), Sum(climtas_calcs), 'climtas_effect'),
        '100,000 * death/population', 'deaths/person/year', lambda x: x / 1e5,
        'convert to deaths/person/year', "Divide by 100000 to convert to deaths/person/year.")

    return calculation, [], covariator.get_current
