import pytest
import pandas as pd
from datastore.irregions import contains_region


@pytest.fixture
def hierid_df():
    """pandas.DataFrame mimicing regions/hierarchy.csv with
    'region-key' column as index
    """
    out = (pd.DataFrame({"region-key": ["Aa", "Ab", "Ba", "Baa", "Ca"], 
                  "parent-key": ["A", "A", "B", "Ba", "C"]})
           .set_index("region-key")
          )
    return out


@pytest.mark.parametrize(
    "query_parent,query_child,expected",
    [
        (["A"], "Aa", True),
        (["B"], "Baa", True),
        (["A", "B"], "Ba", True),
        (["B", "C"], "Baa", True),
        (["C"], "Ba", False),
        (["A"], "Afoobar", False),
        (["A", "C"], "Baa", False),
        (["Aa"], "Aa", True),
    ]
)
def test_contains_region(hierid_df, query_parent, query_child, expected):
    """Test basic casses for contains_region() success
    """
    actual = contains_region(query_parent, query_child, hierid_df)
    assert actual is expected
