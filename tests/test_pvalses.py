"""Check that Pvals dictionaries work as expected
"""

import pytest
import time
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

