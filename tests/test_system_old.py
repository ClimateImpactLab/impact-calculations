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
