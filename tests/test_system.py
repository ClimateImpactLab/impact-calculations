"""
System tests for impact projection system.

These will likely fail if run as installed package. We make strong
assumptions about directory structure. These are also smoke tests,
and are not comprehensive.
"""


import unittest
import subprocess
import os
import os.path
from glob import glob

import numpy as np
import numpy.testing as npt
import xarray as xr
import yaml
import pytest


_here = os.path.abspath(os.path.dirname(__file__))


def test_alwayspass():
    """Work around CI failing run with all deselected tests

    A temporary hack. Currently pytest in CI deselects all tests because of
    infrastructure limits. This returns exit status 5 rather than 0, causing
    CI to fail its  testing stage.

    This test is added so that one test always passes, thus returning status
    code 0.
    """
    pass


@pytest.mark.imperics_shareddir
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

        goal_head = np.array([20.582834,  108.4278,  449.78918])
        goal_tail = np.array([-2572.8152, -3596.9329, -2827.6426])
        npt.assert_allclose(actual[:3, 0], goal_head, atol=1e-4, rtol=0)
        npt.assert_allclose(actual[-3:, 0], goal_tail, atol=1e-4, rtol=0)

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


@pytest.mark.imperics_shareddir
class TestSingleAgcorn(unittest.TestCase):
    """Check diagnostic projection run for ag sector - corn"""

    @classmethod
    def setUpClass(cls):
        """Pre-test setup sets cls.results_nc4 to output xr.Dataset we want to check"""
        cls.results_nc4 = None
        # This is a hack because the projection run scripts can only be launched
        # from the root of the impact-calculations directory.
        # I don't have a way around this as py2.7 unittest doesn't have mocks.
        this_cwd = os.getcwd()
        conf_path = os.path.abspath(os.path.join(_here, 'configs', 'single-agriculture.yml'))
        cmd_path = 'diagnostic.sh'  # Must be run as PWD
        resultspath_fragment = ['temp', 'single', 'rcp85', 'CCSM4', 'high',
                                'SSP3',
                                'corn_global_t-tbar_pbar_lnincbr_ir_tp_binp-tbar_pbar_lnincbr_ir_tp_fe-A1TT_A0Y_clus-A1_A0Y_TINV-191220.nc4']

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

        goal_shape = (118, 1)
        self.assertEqual(actual.shape, goal_shape)

        goal_head = np.array([-0.16533269, -0.0223633,  0.02246693])
        goal_tail = np.array([-0.59789735, -0.10988867, np.nan])
        npt.assert_allclose(actual[:3, 0], goal_head, atol=1e-4, rtol=0)
        npt.assert_allclose(actual[-3:, 0], goal_tail, atol=1e-4, rtol=0)

    def test_ddseasonaltasmax(self):
        """Smoke test shape & (head, tail) values of 'ddseasonaltasmax' in results_nc4"""
        actual = self.results_nc4['ddseasonaltasmax'].values

        goal_shape = (118, 1)
        self.assertEqual(actual.shape, goal_shape)

        goal_head = np.array([-0.04894612, -0.03128264, -0.02922709])
        goal_tail = np.array([-0.08493597, -0.06603191, np.nan])
        npt.assert_allclose(actual[:3, 0], goal_head, atol=1e-4, rtol=0)
        npt.assert_allclose(actual[-3:, 0], goal_tail, atol=1e-4, rtol=0)

    def test_ddseasonalpr(self):
        """Smoke test shape & (head, tail) values of 'ddseasonalpr' in results_nc4"""
        actual = self.results_nc4['ddseasonalpr'].values

        goal_shape = (118, 1)
        self.assertEqual(actual.shape, goal_shape)

        goal_head = np.array([0.00524488, 0.00486552, 0.00480848])
        goal_tail = np.array([0.01309601, 0.01345166, np.nan])
        npt.assert_allclose(actual[:3, 0], goal_head, atol=1e-4, rtol=0)
        npt.assert_allclose(actual[-3:, 0], goal_tail, atol=1e-4, rtol=0)

    def test_year(self):
        """Smoke test (head, tail) of 'year' in results_nc4"""
        actual = self.results_nc4['year'].values

        goal_shape = (118,)
        self.assertEqual(actual.shape, goal_shape)

        goal_head = np.array([1981, 1982, 1983])
        goal_tail = np.array([2096, 2097, 2098])
        npt.assert_array_equal(actual[:3], goal_head)
        npt.assert_array_equal(actual[-3:], goal_tail)

    def test_regions(self):
        """Test 'regions' in results_nc4"""
        actual = str(self.results_nc4['regions'].values.item())

        goal = 'USA.14.608'
        self.assertEqual(actual, goal)


@pytest.mark.imperics_shareddir
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


@pytest.mark.imperics_shareddir
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
        cls.basename = 'FD_FGLS_inter_climGMFD_Exclude_all-issues_break2_semi-parametric_poly2_OTHERIND_other_energy_TINV_clim_income_spline_lininter'
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
            return_code = subprocess.call(['sh', 'tests/testmontecarlo.sh',
                                           str(conf_path)])
            assert return_code == 0, 'command did not return code 0'  # In python 3 we should add a `check=True` arg instead of the assert

            # This is lazy of me.
            # Note these are for "low" projections
            cls.results_low_base_nc4 = xr.open_dataset(os.path.join(*(results_dir_low_fragment + [cls.basename + '.nc4'])))
            cls.results_low_noadapt_nc4 = xr.open_dataset(os.path.join(*(results_dir_low_fragment + [cls.basename + '-noadapt.nc4'])))
            cls.results_low_incadapt_nc4 = xr.open_dataset(os.path.join(*(results_dir_low_fragment + [cls.basename + '-incadapt.nc4'])))
            cls.results_low_histclim_nc4 = xr.open_dataset(os.path.join(*(results_dir_low_fragment + [cls.basename + '-histclim.nc4'])))
            with open(os.path.join(*(results_dir_low_fragment + ['pvals.yml'])), 'r') as fl:
                cls.results_low_pvals_yml = yaml.load(fl, Loader=yaml.SafeLoader)

            # This is for the "high" projections
            with open(os.path.join(*(results_dir_high_fragment + ['pvals.yml'])), 'r') as fl:
                cls.results_high_pvals_yml = yaml.load(fl, Loader=yaml.SafeLoader)

        finally:
            os.chdir(this_cwd)

    def test_pvals(self):
        """Test contents of pvals ymls for low and high projections"""
        goal = {self.basename: {'seed-csvv': 123}, 'histclim': {'seed-yearorder': 123}}
        self.assertEqual(self.results_low_pvals_yml, goal)
        self.assertEqual(self.results_high_pvals_yml, goal)

    def test_rebased(self):
        """Smoke test shape & (head, tail) values of 'rebased' in results_low_base_nc4"""
        actual = self.results_low_base_nc4['rebased'].values

        goal_shape = (120, 1)
        self.assertEqual(actual.shape, goal_shape)

        goal_head = np.array([182.74854, 138.99937, 432.08884])
        goal_tail = np.array([4340.6616, 3850.7495, 3353.314])
        npt.assert_allclose(actual[:3, 0], goal_head, atol=1e-4, rtol=0)
        npt.assert_allclose(actual[-3:, 0], goal_tail, atol=1e-4, rtol=0)

    def test_noadapt_rebased(self):
        """Smoke test shape & (head, tail) of 'rebased' in results_low_noadapt_nc4"""
        actual = self.results_low_noadapt_nc4['rebased'].values

        goal_shape = (120, 1)
        self.assertEqual(actual.shape, goal_shape)

        goal_head = np.array([182.74854, 138.99937, 432.08884])
        goal_tail = np.array([2130.226, 1964.3873, 1609.678])
        npt.assert_allclose(actual[:3, 0], goal_head, atol=1e-4, rtol=0)
        npt.assert_allclose(actual[-3:, 0], goal_tail, atol=1e-4, rtol=0)

    def test_incadapt_rebased(self):
        """Smoke test shape & (head, tail) of 'rebased' in results_low_incadapt_nc4"""
        actual = self.results_low_incadapt_nc4['rebased'].values

        goal_shape = (120, 1)
        self.assertEqual(actual.shape, goal_shape)

        goal_head = np.array([182.74854, 138.99937, 432.08884])
        goal_tail = np.array([4839.495, 4291.672, 3885.245])
        npt.assert_allclose(actual[:3, 0], goal_head, atol=1e-3, rtol=0)
        npt.assert_allclose(actual[-3:, 0], goal_tail, atol=1e-3, rtol=0)

    def test_histclim_rebased(self):
        """Smoke test shape & (head, tail) of 'rebased' in results_low_histclim_nc4"""
        actual = self.results_low_histclim_nc4['rebased'].values

        goal_shape = (120, 1)
        self.assertEqual(actual.shape, goal_shape)

        goal_head = np.array([463.31558, 320.79092, 320.79092])
        goal_tail = np.array([598.6438, 1263.2665,  689.26575])
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


@pytest.mark.imperics_shareddir
class TestMonteCarloAgcorn(unittest.TestCase):
    """Check Monte Carlo projection run for ag sector - corn"""

    @classmethod
    def setUpClass(cls):
        """Pre-test setup sets cls.results_* to result data we want to check"""
        cls.results_base_nc4 = None
        cls.results_noadapt_nc4 = None
        cls.results_incadapt_nc4 = None
        cls.results_histclim_nc4 = None
        cls.results_pvals_yml = None
        cls.basename = 'corn_global_t-tbar_pbar_lnincbr_ir_tp_binp-tbar_pbar_lnincbr_ir_tp_fe-A1TT_A0Y_clus-A1_A0Y_TINV-191220'
        # This is a hack because the projection run scripts can only be launched
        # from the root of the impact-calculations directory.
        # I don't have a way around this as py2.7 unittest doesn't have mocks.
        this_cwd = os.getcwd()
        conf_path = os.path.abspath(os.path.join(_here, 'configs', 'montecarlo-agriculture.yml'))
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
            return_code = subprocess.call(['sh', 'tests/testmontecarlo.sh',
                                           str(conf_path)])
            assert return_code == 0, 'command did not return code 0'  # In python 3 we should add a `check=True` arg instead of the assert

            # This is lazy of me.
            # Note these are for "low" projections
            cls.results_low_base_nc4 = xr.open_dataset(os.path.join(*(results_dir_low_fragment + [cls.basename + '.nc4'])))
            cls.results_low_noadapt_nc4 = xr.open_dataset(os.path.join(*(results_dir_low_fragment + [cls.basename + '-noadapt.nc4'])))
            cls.results_low_incadapt_nc4 = xr.open_dataset(os.path.join(*(results_dir_low_fragment + [cls.basename + '-incadapt.nc4'])))
            cls.results_low_histclim_nc4 = xr.open_dataset(os.path.join(*(results_dir_low_fragment + [cls.basename + '-histclim.nc4'])))
            with open(os.path.join(*(results_dir_low_fragment + ['pvals.yml'])), 'r') as fl:
                cls.results_low_pvals_yml = yaml.load(fl, Loader=yaml.SafeLoader)

            # This is for the "high" projections
            with open(os.path.join(*(results_dir_high_fragment + ['pvals.yml'])), 'r') as fl:
                cls.results_high_pvals_yml = yaml.load(fl, Loader=yaml.SafeLoader)

        finally:
            os.chdir(this_cwd)

    def test_pvals(self):
        """Test contents of pvals ymls for low and high projections"""
        goal = {
            self.basename: {'seed-csvv': 123},
            'FD_FGLS_inter_climGMFD_Exclude_all-issues_break2_semi-parametric_poly2_OTHERIND_other_energy_TINV_clim_income_spline_lininter': {
                'seed-csvv': 123
            },
            'histclim': {'seed-yearorder': 123}
         }
        self.assertEqual(self.results_low_pvals_yml, goal)
        self.assertEqual(self.results_high_pvals_yml, goal)

    def test_rebased(self):
        """Smoke test shape & (head, tail) values of 'rebased' in results_low_base_nc4"""
        actual = self.results_low_base_nc4['rebased'].values

        goal_shape = (118, 1)
        self.assertEqual(actual.shape, goal_shape)

        goal_head = np.array([18437142.0, 15240259.0, 13820419.0])
        goal_tail = np.array([18277254.0, -23021556.0, np.nan])
        npt.assert_allclose(actual[:3, 0], goal_head, atol=1, rtol=0)
        npt.assert_allclose(actual[-3:, 0], goal_tail, atol=1, rtol=0)

    def test_noadapt_rebased(self):
        """Smoke test shape & (head, tail) of 'rebased' in results_low_noadapt_nc4"""
        actual = self.results_low_noadapt_nc4['rebased'].values

        goal_shape = (118, 1)
        self.assertEqual(actual.shape, goal_shape)

        goal_head = np.array([18437142.0, 15240259.0, 13820419.0])
        goal_tail = np.array([18388806.0, -21105998.0, np.nan])
        npt.assert_allclose(actual[:3, 0], goal_head, atol=1, rtol=0)
        npt.assert_allclose(actual[-3:, 0], goal_tail, atol=1, rtol=0)

    def test_incadapt_rebased(self):
        """Smoke test shape & (head, tail) of 'rebased' in results_low_incadapt_nc4"""
        actual = self.results_low_incadapt_nc4['rebased'].values

        goal_shape = (118, 1)
        self.assertEqual(actual.shape, goal_shape)

        goal_head = np.array([18437142.0, 15240259.0, 13820419.0])
        goal_tail = np.array([18388806.0, -21105956.0, np.nan])
        npt.assert_allclose(actual[:3, 0], goal_head, atol=1, rtol=0)
        npt.assert_allclose(actual[-3:, 0], goal_tail, atol=1, rtol=0)

    def test_histclim_rebased(self):
        """Smoke test shape & (head, tail) of 'rebased' in results_low_histclim_nc4"""
        actual = self.results_low_histclim_nc4['rebased'].values

        goal_shape = (118, 1)
        self.assertEqual(actual.shape, goal_shape)

        goal_head = np.array([-2261668.0,  3017162.0, 3017162.0])
        goal_tail = np.array([ 2662714.8, -6997009.5, np.nan])
        npt.assert_allclose(actual[:3, 0], goal_head, atol=1, rtol=0)
        npt.assert_allclose(actual[-3:, 0], goal_tail, atol=1, rtol=0)

    def test_year(self):
        """Smoke test (head, tail) of 'year' in results_low_base_nc4"""
        actual = self.results_low_base_nc4['year'].values

        goal_shape = (118,)
        self.assertEqual(actual.shape, goal_shape)

        goal_head = np.array([1981, 1982, 1983])
        goal_tail = np.array([2096, 2097, 2098])
        npt.assert_array_equal(actual[:3], goal_head)
        npt.assert_array_equal(actual[-3:], goal_tail)

    def test_regions(self):
        """Test 'regions' in results_low_base_nc4"""
        actual = str(self.results_low_base_nc4['regions'].values.item())

        goal = 'USA.14.608'
        self.assertEqual(actual, goal)


@pytest.mark.imperics_shareddir
class TestAggregateEnergy(unittest.TestCase):
    """Check projection aggregation for energy sector
    """

    @classmethod
    def setUpClass(cls):
        """Pre-test setup sets cls.results_* to output xr.Dataset we want to check"""
        cls.results_aggregated = None
        cls.results_levels = None
        # This is a hack because the projection run scripts can only be launched
        # from the root of the impact-calculations directory.
        # I don't have a way around this as py2.7 unittest doesn't have mocks.
        this_cwd = os.getcwd()
        conf_path = os.path.abspath(os.path.join(_here, 'configs', 'aggregate-energy.yml'))
        cmd_path = 'aggregate.sh'  # Must be run in PWD

        resultspath_fragment = ['median', 'rcp45', 'surrogate_CanESM2_89', 'low', 'SSP3',
                                'FD_FGLS_inter_climGMFD_Exclude_all-issues_break2_semi-parametric_poly2_OTHERIND_other_energy_TINV_clim_income_spline-incadapt-withprice']
        # Output files have these fragments tagged on the end.

        # Remove existing aggregation files in output directory!
        # These are files matching glob *aggregated.nc4 and *levels.nc4!
        with open(conf_path) as fl:
            cfg = yaml.load(fl, Loader=yaml.SafeLoader)
        cfg_outpath = cfg['outputdir']
        # cfg_basename = cfg['basename']
        for ending in ['aggregated', 'levels']:
            glob_pattern = os.path.join(*[cfg_outpath] + resultspath_fragment[:-1] + ['*' + ending + '.nc4'])
            for target in glob(glob_pattern):
                print(('removing existing ' + target))
                os.remove(target)

        os.chdir(os.path.join(_here, os.pardir))
        try:
            # !!Not secure!!
            return_code = subprocess.call(['sh', str(cmd_path), str(conf_path)])
            assert return_code == 0, 'command did not return code 0'

            resultspath = os.path.join(*[cfg_outpath] + resultspath_fragment[:-1] + [resultspath_fragment[-1] + '-aggregated.nc4'])
            cls.results_aggregated = xr.open_dataset(resultspath)

            resultspath = os.path.join(*[cfg_outpath] + resultspath_fragment[:-1] + [resultspath_fragment[-1] + '-levels.nc4'])
            cls.results_levels = xr.open_dataset(resultspath)

        finally:
            os.chdir(this_cwd)

    def test_levels_regions(self):
        """Test regions in *levels results file"""
        actual = self.results_levels['regions'].values
        self.assertEqual(actual.shape, (24378, ))
        self.assertEqual(actual[0], 'CAN.1.2.28')
        self.assertEqual(actual[-1], 'BWA.4.13')

    def test_levels_rebased(self):
        """Test shape & (head, tail) values of 'rebased' in *levels file"""
        actual = self.results_levels['rebased'].values

        self.assertEqual(actual.shape, (119, 24378))

        goal_head = np.array([7.7720156, 28.00633, 19.375658])
        goal_tail = np.array([-602.15814, -619.549, -649.28516])
        npt.assert_allclose(actual[:3, 0], goal_head, atol=1e-4, rtol=0)
        npt.assert_allclose(actual[-3:, -1], goal_tail, atol=1e-4, rtol=0)

    def test_aggregated_regions(self):
        """Test regions in *aggregated results file"""
        actual = self.results_aggregated['regions'].values
        self.assertEqual(actual.shape, (5716, ))
        self.assertEqual(actual[0], '')
        self.assertEqual(actual[-1], 'RUS.73.2026')

    def test_aggregated_rebased(self):
        """Test shape & (head, tail) values of 'rebased' in *aggregated file"""
        actual = self.results_aggregated['rebased'].values

        self.assertEqual(actual.shape, (119, 5716))

        goal_head = np.array([2.8525314, 2.285627, 2.2759197])
        goal_tail = np.array([-42.953907, -65.55747, -51.37832])
        npt.assert_allclose(actual[:3, 0], goal_head, atol=1e-4, rtol=0)
        npt.assert_allclose(actual[-3:, -1], goal_tail, atol=1e-4, rtol=0)
