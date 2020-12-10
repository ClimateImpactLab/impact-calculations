"""Check that linear extrapolation works as expected.
"""

import pytest
import numpy as np
import numpy.testing as npt
import xarray as xr
import pandas as pd
from interpret.specification import create_curvegen

def test_polynomial():
    csvv = dict(variables={'tas': {'unit': 'C'}, 'tas-poly-2': {'unit': 'C2'}, 'outcome': {'unit': 'widgets'}},
                prednames=['tas', 'tas-poly-2'], covarnames=['1', '1'], gamma=[1, 1])
    specconf = {"description": "Simple polynomial",
                "depenunit": "widgets",
                "indepunit": "C",
                "functionalform": "polynomial",
                "variable": "tas",
                "extrapolation": {
                    "indepvar": "tas",
                    "margin": .1,
                    "bounds": (0, 1)
                }}
    curvegen = create_curvegen(csvv, None, 'TrinLand', specconf=specconf)
    clipcurve = curvegen.get_curve('TrinLand', 2000, {})

    ds0 = xr.Dataset({'tas': (['time'], [0, .5, 1]),
                      'tas-poly-2': (['time'], np.array([0, .5, 1]) ** 2)},
                     coords={'time': pd.date_range('1800-01-01', periods=3)})
    yy0 = clipcurve(ds0)

    ds1 = xr.Dataset({'tas': (['time'], [-.2, -.1, .5, 1.2, 1.3]),
                      'tas-poly-2': (['time'], np.array([-.2, -.1, .5, 1.2, 1.3]) ** 2)},
                     coords={'time': pd.date_range('1800-01-01', periods=5)})

    slope0 = -1.1
    slope1 = 2.9

    yy1 = clipcurve(ds1)
    desired = [yy0[0] + .2 * slope0, yy0[0] + .1 * slope0, yy0[1], yy0[2] + .2 * slope1, yy0[2] + .3 * slope1]
    npt.assert_allclose(yy1, desired)

    specconf['extrapolation']['bounds'] = {'tas': [0, 1]}

    curvegen = create_curvegen(csvv, None, 'TrinLand', specconf=specconf)
    clipcurve = curvegen.get_curve('TrinLand', 2000, {})

    yy1 = clipcurve(ds1)
    desired = [yy0[0] + .2 * slope0, yy0[0] + .1 * slope0, yy0[1], yy0[2] + .2 * slope1, yy0[2] + .3 * slope1]
    npt.assert_allclose(yy1, desired)
