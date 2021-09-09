"""Check that Pvals dictionaries work as expected
"""

import time
import numpy as np
from adaptation.csvvfile import collapse_bang
from generate import pvalses


def test_getseed():
    """Check that different pvals objects with the same
    `relative_location` produce same & different values as expected."""
    
    pvals1 = pvalses.OnDemandRandomPvals(["one", "two"])
    pvals2 = pvalses.OnDemandRandomPvals(["one", "two"])

    seed_unique1 = pvals1['something'].get_seed('whatever')
    seed_common1 = pvals1['histclim'].get_seed('whoknows')

    time.sleep(1) # make sure that we have a different time seed
    
    seed_unique2 = pvals2['something'].get_seed('whatever')
    seed_common2 = pvals2['histclim'].get_seed('whoknows')

    assert seed_unique1 != seed_unique2
    assert seed_common1 == seed_common2


def test_ondemandrandomdictionary_seedio(tmpdir):
    """Test that OnDemandRandomPvals seeds can be written and then read without changing seed"""
    # Make Pvals, get seed, dump pvals to tmp file.
    pvals1 = pvalses.OnDemandRandomPvals(relative_location=None)
    seed1 = pvals1["idontknow"].get_seed("whatever")
    pvalses.make_pval_file(tmpdir, pvals1)

    # Create new pvals from file, get seed. Compare.
    pvals2 = pvalses.read_pval_file(tmpdir, relative_location=None)
    seed2 = pvals2["idontknow"].get_seed("whatever")

    assert seed1 == seed2


def test_ondemandrandomdictionary_feeds_collapsebang():
    """Test that OnDemandRandomPvals seeds can be fed to adaptation.csvvfile.collapse_bang"""
    # Made up simple parameters for MVN distribution.
    gamma_original = np.array([0.5, -0.2])
    d = {"gammavcv": np.array([[2.0, 0.3], [0.3, 0.5]]), "gamma": gamma_original.copy()}

    pvals = pvalses.OnDemandRandomPvals(relative_location=None)
    seed = pvals["foo"].get_seed("bar")

    collapse_bang(data=d, seed=seed)  # Modifies `d` in place.

    # Just check that there was a change-in-place without error...
    assert (d["gamma"] != gamma_original).all()
