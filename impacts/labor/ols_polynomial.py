"""
Compute minutes lost due to temperature effects as OLS polynomial
"""

import numpy as np
from openest.models.curve import StepCurve, ProductCurve, CoefficientsCurve
from openest.generate.stdlib import Sum, YearlyAverageDay

from adaptation.curvegen import ConstantCurveGenerator, TransformCurveGenerator
from adaptation.curvegen_known import PolynomialCurveGenerator


def prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer='full', config={}):
    """

    Parameters
    ----------
    csvv : dict
    weatherbundle :
        Unused.
    economicmodel :
        Unused.
    qvals :
        Unused.
    farmer : str
        Unused.
    config :
        Unused.

    Returns
    -------
    calculation : openest.generate.stdlib.Sum
    depends_on : sequence
    get_covariator : callable
        This accepts "region" arg, which does nothing.  It returns
        ``{'climtas': None, 'loggdppc': None}``.
    """
    order = len(set(csvv['prednames'])) - 1  # -1 because of belowzero
    print('Order ' + str(order))

    temp_curvegen = PolynomialCurveGenerator(['C'] + ['C^%d' % i for i in range(2, order + 1)],
                                             'minutes worked by individual', 'tasmax', order, csvv)

    def prep_curvegen(region, curve):
        return ProductCurve(CoefficientsCurve(curve.ccs, curve), StepCurve([-np.inf, 0, np.inf], [0, 1], lambda x: x[:, 0]))
    
    postemp_curvegen = TransformCurveGenerator(prep_curvegen, temp_curvegen)
    
    # Monkeypatch a new get_curve method that removes "weather" keyword arg.
    # This is alternative to creating new FarmerCurveGenerator class for this
    # single use case.
    postemp_curvegen._get_curve = postemp_curvegen.get_curve

    def get_curve_monkeypatch(*args, **kwargs):
        """Monkeypatched ``get_curve()`` method, dropping any weather arg"""
        if 'weather' in kwargs:
            del kwargs['weather']
        return postemp_curvegen._get_curve(*args, **kwargs)
    postemp_curvegen.get_curve = get_curve_monkeypatch

    tempeffect = YearlyAverageDay('minutes worked by individual',
                                  postemp_curvegen,
                                  'the temperature effect')

    # Because we have a cutoff term for days less than 0 C...
    zerocurvegen = ConstantCurveGenerator('C', 'minutes worked by individual',
                                          StepCurve([-np.inf, 0, np.inf],
                                                    [csvv['gamma'][-1], 0],
                                                    lambda x: x[:, 0]))
    zeroeffect = YearlyAverageDay('minutes worked by individual',
                                  zerocurvegen,
                                  'effect from days less than 0 C')

    calculation = Sum([tempeffect, zeroeffect])
    depends_on = []

    # Return None for climtas and loggdppc as this uses no covariations,
    # these keys required by generate.generate.push_callback()
    def get_covariator(region):
        return dict(climtas=None, loggdppc=None)

    return calculation, depends_on, get_covariator
