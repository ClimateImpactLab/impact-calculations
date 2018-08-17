import re
import numpy as np
from adaptation import csvvfile, curvegen, curvegen_arbitrary, covariates
from openest.models.curve import StepCurve, OtherClippedCurve
from openest.generate.stdlib import *

def prepare_interp_raw(csvv, weatherbundle, economicmodel, pvals, farmer='full', config={}):
    covariator = covariates.CombinedCovariator([covariates.TranslateCovariator(covariates.MeanWeatherCovariator(weatherbundle, 2015, config=config.get('climcovar', {}), varindex=0), {'climtas': 'tas'}),
                                                covariates.EconomicCovariator(economicmodel, 2015, config=config.get('econcovar', {}))])

    curr_curvegen = curvegen_arbitrary.CoefficientsCurveGenerator(curvegen_arbitrary.ParameterHolderCurve, ['C days'] * (len(set(csvv['prednames']))), '100,000 * death/population', csvv)
    farm_curvegen = curvegen.FarmerCurveGenerator(curr_curvegen, covariator, farmer)

    def hdd_transform(region, curve):
        coeff = curve.params['hdd']
        return FlatCurve(max(coeff, 0))

    def cdd_transform(region, curve):
        coeff = curve.params['cdd']
        return FlatCurve(max(coeff, 0))

    def hdd_transform_climtas(region, curve):
        if curve.params['hdd'] < 0:
            return FlatCurve(0)
        else:
            return FlatCurve(get_gamma(csvv, 'hdd', 'climtas'))

    def cdd_transform_climtas(region, curve):
        if curve.params['cdd'] < 0:
            return FlatCurve(0)
        else:
            return FlatCurve(get_gamma(csvv, 'cdd', 'climtas'))

    hdd_curvegen = curvegen.TransformCurveGenerator(hdd_transform, "HDD clipped curve", farm_curvegen)
    cdd_curvegen = curvegen.TransformCurveGenerator(cdd_transform, "CDD clipped curve", farm_curvegen)
    hdd_curvegen_climtas = curvegen.TransformCurveGenerator(hdd_transform_climtas, "HDD clipped climtas curve", farm_curvegen)
    cdd_curvegen_climtas = curvegen.TransformCurveGenerator(cdd_transform_climtas, "CDD clipped climtas curve", farm_curvegen)

    # Collect all baselines
    calculation = Transform(
        AuxillaryResult(
            HotColdAnnual('100,000 * death/population', hdd_curvegen, cdd_curvegen,
                          "the mortality response curve")
            HotColdAnnual('100,000 * death/population', hdd_curvegen_climtas, cdd_curvegen_climtas,
                          "climtas effect after clipping", norecord=True), 'climtas_effect'),
        '100,000 * death/population', 'deaths/person/year', lambda x: x / 1e5,
        'convert to deaths/person/year', "Divide by 100000 to convert to deaths/person/year.")

    return calculation, [], covariator.get_current
