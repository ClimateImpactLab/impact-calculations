"""
System tests for impact projection system.

These will likely fail if run as installed package. We make some strong
assumptions about directory structure.
"""


import unittest
import subprocess
import os
import os.path

import numpy as np
import numpy.testing as npt
import xarray as xr
import yaml


_here = os.path.abspath(os.path.dirname(__file__))


class TestSingleEnergy(unittest.TestCase):
    """Check diagnostic projection run for energy sector"""

    @classmethod
    def setUpClass(cls):
        """Pre-test setup sets cls.results_nc4 to output xr.Dataset we want to check"""
        cls.results_nc4 = None
        # This is a hack because the projection run scripts can only be launched
        # from the root of the impact-calculations directory.
        # I don't have a way around this as py2.7 unittest doesn't have mocks.
        this_cwd = os.getcwd()
        conf_path = os.path.abspath(os.path.join(_here, 'configs', 'single-energy.yml'))
        cmd_path = 'diagnostic.sh'  # Must be run as PWD
        resultspath_fragment = ['temp', 'single', 'rcp85', 'CCSM4', 'high',
                                'SSP3',
                                'FD_FGLS_inter_climGMFD_Exclude_all-issues_break2_semi-parametric_poly2_OTHERIND_other_energy_TINV_clim_income_spline_lininter.nc4']
        
        os.chdir(os.path.join(_here, os.pardir))
        try:
            # This is going to *clobber* anything in the 
            # "impact-calculations/temp" directory.

            # !!Not secure!!
            return_code = subprocess.call(['sh', str(cmd_path), str(conf_path)])
            assert return_code == 0, 'command did not return code 0'

            resultspath = os.path.join(*resultspath_fragment)
            cls.results_nc4 = xr.open_dataset(resultspath)

        finally:
            os.chdir(this_cwd)

    def test_rebased(self):
        """Smoke test shape & (head, tail) values of 'rebased' in results_nc4"""
        actual = self.results_nc4['rebased'].values

        goal_shape = (120, 1)
        self.assertEqual(actual.shape, goal_shape)

        goal_head = np.array([20.58283424,  108.42780304,  449.78918457])
        goal_tail = np.array([-2572.81518555, -3596.93286133, -2827.64257812])
        npt.assert_allclose(actual[:3, 0], goal_head, atol=1e-8, rtol=0)
        npt.assert_allclose(actual[-3:, 0], goal_tail, atol=1e-8, rtol=0)

    def test_year(self):
        """Smoke test (head, tail) of 'year' in results_nc4"""
        actual = self.results_nc4['year'].values

        goal_shape = (120,)
        self.assertEqual(actual.shape, goal_shape)

        goal_head = np.array([1981, 1982, 1983])
        goal_tail = np.array([2098, 2099, 2100])
        npt.assert_array_equal(actual[:3], goal_head)
        npt.assert_array_equal(actual[-3:], goal_tail)

    def test_regions(self):
        """Test 'regions' in results_nc4"""
        actual = str(self.results_nc4['regions'].values.item())

        goal = 'USA.14.608'
        self.assertEqual(actual, goal)


class TestSingleMortality(unittest.TestCase):
    """Check diagnostic projection run for mortality sector"""

    @classmethod
    def setUpClass(cls):
        """Pre-test setup sets cls.results_nc4 to output xr.Dataset we want to check"""
        cls.results_nc4 = None
        # This is a hack because the projection run scripts can only be launched
        # from the root of the impact-calculations directory.
        # I don't have a way around this as py2.7 unittest doesn't have mocks.
        this_cwd = os.getcwd()
        conf_path = os.path.abspath(os.path.join(_here, 'configs', 'single-mortality.yml'))
        cmd_path = 'diagnostic.sh'  # Must be run as PWD
        resultspath_fragment = ['temp', 'single', 'rcp85', 'CCSM4', 'high',
                                'SSP3',
                                'Agespec_interaction_GMFD_POLY-4_TINV_CYA_NW_w1-combined.nc4']
        
        os.chdir(os.path.join(_here, os.pardir))
        try:
            # This is going to *clobber* anything in the 
            # "impact-calculations/temp" directory.

            # !!Not secure!!
            return_code = subprocess.call(['sh', str(cmd_path), str(conf_path)])
            assert return_code == 0, 'command did not return code 0'

            resultspath = os.path.join(*resultspath_fragment)
            cls.results_nc4 = xr.open_dataset(resultspath)

        finally:
            os.chdir(this_cwd)

    def test_rebased(self):
        """Smoke test shape & (head, tail) values of 'rebased' in results_nc4"""
        actual = self.results_nc4['rebased'].values

        goal_shape = (120, 1)
        self.assertEqual(actual.shape, goal_shape)

        goal_head = np.array([3.65776723e-05,   1.39244206e-04,   4.28901607e-04])
        goal_tail = np.array([-0.00160056, -0.00192268, -0.00181685])
        npt.assert_allclose(actual[:3, 0], goal_head, atol=1e-8, rtol=0)
        npt.assert_allclose(actual[-3:, 0], goal_tail, atol=1e-8, rtol=0)

    def test_year(self):
        """Smoke test (head, tail) of 'year' in results_nc4"""
        actual = self.results_nc4['year'].values

        goal_shape = (120,)
        self.assertEqual(actual.shape, goal_shape)

        goal_head = np.array([1981, 1982, 1983])
        goal_tail = np.array([2098, 2099, 2100])
        npt.assert_array_equal(actual[:3], goal_head)
        npt.assert_array_equal(actual[-3:], goal_tail)

    def test_regions(self):
        """Test 'regions' in results_nc4"""
        actual = str(self.results_nc4['regions'].values.item())

        goal = 'USA.14.608'
        self.assertEqual(actual, goal)


class TestMonteCarloEnergy(unittest.TestCase):
    """Check Monte Carlo projection run for energy sector"""

    @classmethod
    def setUpClass(cls):
        """Pre-test setup sets cls.results_* to result data we want to check"""
        cls.results_base_nc4 = None
        cls.results_noadapt_nc4 = None
        cls.results_incadapt_nc4 = None
        cls.results_histclim_nc4 = None
        cls.results_pvals_yml = None
        # This is a hack because the projection run scripts can only be launched
        # from the root of the impact-calculations directory.
        # I don't have a way around this as py2.7 unittest doesn't have mocks.
        this_cwd = os.getcwd()
        conf_path = os.path.abspath(os.path.join(_here, 'configs', 'montecarlo-energy.yml'))
        results_dir_low_fragment = ['temp', 'batch0', 'rcp85', 'CCSM4', 'low',
                                    'SSP3']
        results_dir_high_fragment = ['temp', 'batch0', 'rcp85', 'CCSM4', 'high',
                                     'SSP3']

        os.chdir(os.path.join(_here, os.pardir))
        try:
            # This is going to *clobber* anything in the
            # "impact-calculations/temp" directory.

            # !!Not secure!!
            # return_code = subprocess.call(['nohup', 'python', '-m', 'generate.generate',
                                           # str(conf_path),
                                           # '--filter-region=USA.14.608',
                                           # '--outputdir=$PWD/temp'])

            # Call external shell script as hack to get around control returning to the
            # test too early.
            return_code = subprocess.call(['sh', 'tests/testmontecarloenergy.sh', 
                                           str(conf_path)])
            assert return_code == 0, 'command did not return code 0'

            # This is lazy of me.
            # Note these are for "low" projections
            cls.results_low_base_nc4 = xr.open_dataset(os.path.join(*(results_dir_low_fragment + ['FD_FGLS_inter_climGMFD_Exclude_all-issues_break2_semi-parametric_poly2_OTHERIND_other_energy_TINV_clim_income_spline_lininter.nc4'])))
            cls.results_low_noadapt_nc4 = xr.open_dataset(os.path.join(*(results_dir_low_fragment + ['FD_FGLS_inter_climGMFD_Exclude_all-issues_break2_semi-parametric_poly2_OTHERIND_other_energy_TINV_clim_income_spline_lininter-noadapt.nc4'])))
            cls.results_low_incadapt_nc4 = xr.open_dataset(os.path.join(*(results_dir_low_fragment + ['FD_FGLS_inter_climGMFD_Exclude_all-issues_break2_semi-parametric_poly2_OTHERIND_other_energy_TINV_clim_income_spline_lininter-incadapt.nc4'])))
            cls.results_low_histclim_nc4 = xr.open_dataset(os.path.join(*(results_dir_low_fragment + ['FD_FGLS_inter_climGMFD_Exclude_all-issues_break2_semi-parametric_poly2_OTHERIND_other_energy_TINV_clim_income_spline_lininter-histclim.nc4'])))
            with open(os.path.join(*(results_dir_low_fragment + ['pvals.yml'])), 'r') as fl:
                cls.results_low_pvals_yml = yaml.load(fl, Loader=yaml.SafeLoader)

            # This is for the "high" projections
            with open(os.path.join(*(results_dir_high_fragment + ['pvals.yml'])), 'r') as fl:
                cls.results_high_pvals_yml = yaml.load(fl, Loader=yaml.SafeLoader)

        finally:
            os.chdir(this_cwd)

    def test_pvals(self):
        """Test contents of pvals ymls for low and high projections"""
        goal = {'FD_FGLS_inter_climGMFD_Exclude_all-issues_break2_semi-parametric_poly2_OTHERIND_other_energy_TINV_clim_income_spline_lininter':
                    {'seed-csvv': 123}, 'histclim': {'seed-yearorder': 123}}
        self.assertEqual(self.results_low_pvals_yml, goal)
        self.assertEqual(self.results_high_pvals_yml, goal)

    def test_rebased(self):
        """Smoke test shape & (head, tail) values of 'rebased' in results_low_base_nc4"""
        actual = self.results_low_base_nc4['rebased'].values

        goal_shape = (120, 1)
        self.assertEqual(actual.shape, goal_shape)

        goal_head = np.array([-2.4366903, 6.2031026, 145.13083])
        goal_tail = np.array([-955.6651, -1132.2704,  -897.3365])
        npt.assert_allclose(actual[:3, 0], goal_head, atol=1e-4, rtol=0)
        npt.assert_allclose(actual[-3:, 0], goal_tail, atol=1e-4, rtol=0)

    def test_noadapt_rebased(self):
        """Smoke test shape & (head, tail) of 'rebased' in results_low_noadapt_nc4"""
        actual = self.results_low_noadapt_nc4['rebased'].values

        goal_shape = (120, 1)
        self.assertEqual(actual.shape, goal_shape)

        goal_head = np.array([-2.4366903, 6.2031026, 145.13083])
        goal_tail = np.array([-456.83188, -691.3481, -365.40518])
        npt.assert_allclose(actual[:3, 0], goal_head, atol=1e-4, rtol=0)
        npt.assert_allclose(actual[-3:, 0], goal_tail, atol=1e-4, rtol=0)

    def test_incadapt_rebased(self):
        """Smoke test shape & (head, tail) of 'rebased' in results_low_incadapt_nc4"""
        actual = self.results_low_incadapt_nc4['rebased'].values

        goal_shape = (120, 1)
        self.assertEqual(actual.shape, goal_shape)

        goal_head = np.array([-2.4366903, 6.2031026, 145.13083])
        goal_tail = np.array([-456.83188, -691.3481, -365.40518])
        npt.assert_allclose(actual[:3, 0], goal_head, atol=1e-4, rtol=0)
        npt.assert_allclose(actual[-3:, 0], goal_tail, atol=1e-4, rtol=0)

    def test_histclim_rebased(self):
        """Smoke test shape & (head, tail) of 'rebased' in results_low_histclim_nc4"""
        actual = self.results_low_histclim_nc4['rebased'].values

        goal_shape = (120, 1)
        self.assertEqual(actual.shape, goal_shape)

        goal_head = np.array([-50.942883,  59.279816,  59.279816])
        goal_tail = np.array([-89.44237, -233.28142,  -51.416748])
        npt.assert_allclose(actual[:3, 0], goal_head, atol=1e-4, rtol=0)
        npt.assert_allclose(actual[-3:, 0], goal_tail, atol=1e-4, rtol=0)

    def test_year(self):
        """Smoke test (head, tail) of 'year' in results_low_base_nc4"""
        actual = self.results_low_base_nc4['year'].values

        goal_shape = (120,)
        self.assertEqual(actual.shape, goal_shape)

        goal_head = np.array([1981, 1982, 1983])
        goal_tail = np.array([2098, 2099, 2100])
        npt.assert_array_equal(actual[:3], goal_head)
        npt.assert_array_equal(actual[-3:], goal_tail)

    def test_regions(self):
        """Test 'regions' in results_low_base_nc4"""
        actual = str(self.results_low_base_nc4['regions'].values.item())

        goal = 'USA.14.608'
        self.assertEqual(actual, goal)


if __name__ == '__main__':
    unittest.main()
