"""
System tests for mortality impact projection system.

These will likely fail if run as installed package. We make strong
assumptions about directory structure. These are also smoke tests,
and are not comprehensive.

This system test uses the old style of system test as the sector is only
supported in the older Python 2.x code releases.
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


@pytest.mark.skip(reason="mortality sector projection is currently unimplemented")
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
