import unittest
import numpy as np
from adaptation import covariates

class TestCovariates(unittest.TestCase):
    def test_spline_covariator(self):
        """Test the SplineCovariator class with two dummy spline terms."""
        testcovar = covariates.GlobalExogenousCovariator(2015, 'val', 0, np.arange(1, 100))
        splinecovar = covariates.SplineCovariator(testcovar, 'val', 'spline', [5, 10])

        for year in range(2010, 2030):
            covars = splinecovar.offer_update('Nowhere', year, None)
            valspline1 = ((year - 2015) - 5) * ((year - 2015) - 5 > 0)
            valspline2 = ((year - 2015) - 10) * ((year - 2015) - 10 > 0)
            self.assertEqual(covars['valspline1'], valspline1)
            self.assertEqual(covars['valspline2'], valspline2)
            self.assertEqual(len(covars), 2)

if __name__ == '__main__':
    unittest.main()
