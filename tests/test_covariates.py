"""
Various unittess for adaptation.covariates.
"""

import pytest
import unittest
import numpy as np
import pandas as pd
from adaptation import covariates
from adaptation import econmodel
from impactlab_tools.utils import files

@pytest.fixture
def hierid_df():
    """pandas.DataFrame mimicing regions/hierarchy.csv with
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

def get_fractional_change(scalar=1, baseline_year=2050, future_year=2051):
    """Helper for test_scale_covariate_change : returns a float, the (potentially scaled) fractional change of an economic covariate between baseline and future"""
    if scalar==1:
        # testing the classe's ability to understand inexistence of key
        scalar_config={}
    elif scalar=='slowadapt':
        # testing the classe's ability to understandy legacy config implicit rescaling 
        scalar_config={"slowadapt" : 'income'}
    else : 
        # testing the classe's ability to do explicit rescaling 
        scalar_config={"scale-covariate-changes" : {'income' : scalar}}

    econ_covar = covariates.EconomicCovariator(economicmodel=econmodel.SSPEconomicModel('low', 'SSP3', [], {}), maxbaseline=2015, config=scalar_config)
    baseline_covar = econ_covar.offer_update('USA.14.608', baseline_year, None)
    future_covar = econ_covar.offer_update('USA.14.608', future_year, None)
    fractional_change = (future_covar['loggdppc']-baseline_covar['loggdppc'])/baseline_covar['loggdppc'] #simple fractional change : fractional_change = (X_t - X_t-1) / X_t-1
    return fractional_change

@pytest.mark.imperics_shareddir
def test_scale_covariate_change():
    """Test the scale-covariate-changes option in EconomicCovariator and MeanWeatherCovariator.

    the scale-covariate-changes parameter is a scalar that rescales the fractional change of a covariate between a base year and a future year, and this is performed 
    in the system by changing the value of the covariate in the future year.

    this test method approach is to retrieve covariate values passing various values to scale-covariate-changes and verify that the fractional change is 
    appropriately rescaled (or left as is)"""

    real_change = get_fractional_change() # getting some arbitrary fractional change
    
    # test slowadapt legacy (scalar==0.5). Expects to obtain a value equal to half real_change. 
    slow_change = get_fractional_change('slowadapt')
    if real_change>0: # separating out the usual case to the zero fractional change case. 
        #rounding at first decimal place, can't obtain better. Approximation with the log form ?
        np.testing.assert_approx_equal(slow_change/real_change, 0.5, 2)
    else:
        np.testing.assert_approx_equal(slow_change, 0)

    # test arbitrary scalar c. Expects to obtain a value equal to real_change * c.
    fast_change = get_fractional_change(2)
    if real_change>0:
        np.testing.assert_approx_equal(fast_change/real_change, 2, 2)
    else:
        np.testing.assert_approx_equal(fast_change, 0)


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

if __name__ == "__main__":
    unittest.main()
