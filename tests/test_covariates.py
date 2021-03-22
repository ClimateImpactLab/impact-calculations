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

def get_g(scalar=1, baseline_year=2050, future_year=2051):
    """Helper for test_scale_covariate_change : returns a float, the (potentially scaled) growth rate of an economic covariate between baseline and future"""
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
    g = (future_covar['loggdppc']-baseline_covar['loggdppc'])/baseline_covar['loggdppc']
    return g


def test_scale_covariate_change(monkeypatch):
    """Test the scale-covariate-changes option in EconomicCovariator and MeanWeatherCovariator."""
    monkeypatch.setattr(files, 'server_config', {'shareddir': '/shares/gcp'})
    real_g = get_g()
    
    # test slowadapt legacy (scalar==0.5)
    slow_g = get_g('slowadapt')
    if real_g>0:
        #rounding at first decimal place, can't obtain better. Approximation with the log form ?
        scale = round(slow_g/real_g,1)
        error = "expected slow/real g to be equal to 0.5 but I got" + str(scale)
        assert scale==0.50, error
    else:
        error = "real g is equal to 0, expected slow g to be equal to 0 but I got" + str(slow_g)
        assert slow_g==0, error

    # test arbitrary scalar
    fast_g = get_g(2)
    if real_g>0:
        scale = round(fast_g/real_g,1)
        error = "expected fast/real g to be equal to 2 but I got" + str(scale)
        assert scale==2.00, error
    else:
        error = "real g is equal to 0, expected fast g to be equal to 2 but I got" + str(fast_g)
        assert fast_g==0, error


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
