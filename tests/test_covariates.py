"""
Various unittess for adaptation.covariates.
"""

import pytest
import unittest
import numpy as np
import pandas as pd
from adaptation import covariates


@pytest.fixture
def hierid_df():
    """pandas.DataFrame mimicing /shares/gcp/regions/hierarchy.csv with
    'region-key' column as index
    """
    out = pd.DataFrame(
        {
            "region-key": ["Aa", "Ab", "Ba", "Baa", "Ca"],
            "parent-key": ["A", "A", "B", "Ba", "C"],
        }
    ).set_index("region-key")
    return out


def test_populate_constantcovariator_by_hierid(hierid_df):
    """Basic test of populate_constantcovariator_by_hierid()
    """
    ccovar = covariates.populate_constantcovariator_by_hierid(
        "hierid-foobar", ["A"], hierid_df
    )

    assert ccovar.get_current("Ab") == {"hierid-foobar": 1.0}
    assert ccovar.get_current("Baa") == {"hierid-foobar": 0.0}

    assert ccovar.get_update("Ab", 1984, "ni!") == {"hierid-foobar": 1.0}
    assert ccovar.get_update("Baa", 1984, "ni!") == {"hierid-foobar": 0.0}


class TestCovariates(unittest.TestCase):
    def test_spline_covariator(self):
        """Test the SplineCovariator class with two dummy spline terms."""
        testcovar = covariates.GlobalExogenousCovariator(
            2015, "val", 0, np.arange(1, 100)
        )
        splinecovar = covariates.SplineCovariator(testcovar, "spline", [5, 10])

        for year in range(2010, 2030):
            covars = splinecovar.offer_update("Nowhere", year, None)
            valspline1 = ((year - 2015) - 5) * ((year - 2015) - 5 > 0)
            valspline2 = ((year - 2015) - 10) * ((year - 2015) - 10 > 0)
            self.assertEqual(covars["valspline1"], valspline1)
            self.assertEqual(covars["valspline2"], valspline2)
            self.assertEqual(len(covars), 4) # 2 spline terms, 2 indicators

    def get_g(scalar=1, baseline=2050, future=2051):
        """Helper for test_scale_covariates_change : returns a float, the (potentially scaled) growth rate of an economic covariate between baseline and future"""
        scalarconfig={"scale-covariate-changes" : {'income' : scalar}}
        econcovar = covariates.EconomicCovariator(economicmodel=adaptation.SSPEconomicModel('low', 'SSP3', [], {}), maxbaseline=2015, config=scalarconfig)
        baseline = econcovar.offer_update('USA.14.608', baseline_year)
        future = econcovar.offer_update('USA.14.608', future_year)
        g = (future-baseline)/baseline 
        return g

    def test_scale_covariates_change(self):
        """Test the scale-covariate-changes option in EconomicCovariator and MeanWeatherCovariator."""
        testcovar = covariates.GlobalExogenousCovariator(
            2015, "val", 0, np.arange(1, 100)
        )

        real_g = get_g()
        slow_g = get_g(0.5)
        self.assertEqual(slow_g, real_g*0.5)
        fast_g = get_g(2)
        self.assertEqual(fast_g, real_g*2)



if __name__ == "__main__":
    unittest.main()
