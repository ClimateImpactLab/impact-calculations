import pytest
import pandas as pd
from adaptation.covariates import populate_constantcovariator_by_hierid


@pytest.fixture
def hierid_df():
    """pandas.DataFrame mimicing /shares/gcp/regions/hierarchy.csv with
    'region-key' column as index
    """
    out = (pd.DataFrame({"region-key": ["Aa", "Ab", "Ba", "Baa", "Ca"], 
                         "parent-key": ["A", "A", "B", "Ba", "C"]})
             .set_index("region-key")
          )
    return out


def test_populate_constantcovariator_by_hierid(hierid_df):
    """Basic test of populate_constantcovariator_by_hierid()
    """
    ccovar = populate_constantcovariator_by_hierid("hierid-foobar", ["A"], hierid_df)
    
    assert ccovar.get_current("Ab") == {"hierid-foobar": 1.0}
    assert ccovar.get_current("Baa") == {"hierid-foobar": 0.0}

    assert ccovar.get_update("Ab") == {"hierid-foobar": 1.0}
    assert ccovar.get_update("Baa") == {"hierid-foobar": 0.0}
