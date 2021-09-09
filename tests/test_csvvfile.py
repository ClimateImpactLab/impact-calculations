from adaptation.csvvfile import collapse_bang

import numpy as np
import numpy.testing as npt


def test_collapse_bang():
    """Test that adaptation.csvvfile.collapse_bang basic seeding behavior"""
    d = {"gammavcv": np.array([[2.0, 0.3], [0.3, 0.5]]), "gamma": np.array([0.5, -0.2])}

    # Feed it a 128 bit int...
    collapse_bang(d, 279206319560455028429841479615391564344)  # This modifies `d` in place...

    npt.assert_allclose(
        d["gamma"],
        np.array([0.5065596667612506, -0.2805661230276253]),
        rtol=1e-15,
    )
    assert d["gammavcv"] is None
