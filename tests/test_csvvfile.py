from adaptation.csvvfile import collapse_bang

import numpy as np
import numpy.testing as npt


def test_collapse_bang():
    """Test that adaptation.csvvfile.collapse_bang basic seeding behavior"""
    d = {"gammavcv": np.array([[2.0, 0.3], [0.3, 0.5]]), "gamma": np.array([0.5, -0.2])}

    collapse_bang(d, 123)  # Modifies `d` in place.

    npt.assert_allclose(
        d["gamma"],
        np.array([1.9038086281574356, 0.745770823978362]),
    )
    assert d["gammavcv"] is None
