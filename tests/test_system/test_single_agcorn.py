"""System smoke tests for a single, diagnostic run for the ag (corn) sector.

These will likely fail if run as installed package as we unfortunately make
strong assumptions about directory structure. These are also smoke tests,
and are not comprehensive.
"""

from pathlib import Path

import pytest
import xarray as xr
import numpy as np
import numpy.testing as npt

from generate.generate import tmpdir_projection


pytestmark = pytest.mark.imperics_shareddir


@pytest.fixture(scope="module")
def projection_netcdf():
    """Runs the projection in tmpdir, gets results netCDF, cleans output on exit
    """
    run_configs = {
        "module": "tests/configs/corn_prsplitmodel_partiald.yml",
        "mode": "writecalcs",
        "singledir": "single",
        "filter-region": "USA.14.608",
        "do_farmers": False,
        "do_historical": False,
        "deltamethod": False,
    }
    # Trigger projection run in temprary directory:
    with tmpdir_projection(run_configs, "single agcorn test") as tmpdirname:
        results_nc_path = Path(
            tmpdirname,
            "single/rcp85/CCSM4/high/SSP3",
            "corn_global_t-tbar_pbar_lnincbr_ir_tp_binp-tbar_pbar_lnincbr_ir_tp_fe-A1TT_A0Y_clus-A1_A0Y_TINV-191220.nc4",
        )
        yield xr.open_dataset(results_nc_path)


def test_region(projection_netcdf):
    """Test the 'regions' dimension of output netCDF
    """
    assert str(projection_netcdf["regions"].values.item()) == "USA.14.608"


class TestYear:
    """Test netCDF output 'year' dimension
    """

    target_variable = "year"

    def test_shape(self, projection_netcdf):
        """Test variable array shape"""
        assert projection_netcdf[self.target_variable].values.shape == (118,)

    def test_head(self, projection_netcdf):
        """Test head of variable array"""
        npt.assert_array_equal(
            projection_netcdf[self.target_variable].values[:3],
            np.array([1981, 1982, 1983]),
        )

    def test_tail(self, projection_netcdf):
        """Test tail of variable array"""
        npt.assert_array_equal(
            projection_netcdf[self.target_variable].values[-3:],
            np.array([2096, 2097, 2098]),
        )


class TestRebased:
    """Test netCDF output 'rebased' variable
    """

    target_variable = "rebased"
    atol = 1e-4
    rtol = 0

    def test_shape(self, projection_netcdf):
        """Test variable array shape"""
        assert projection_netcdf[self.target_variable].values.shape == (118, 1)

    def test_head(self, projection_netcdf):
        """Test head of variable array"""
        npt.assert_allclose(
            projection_netcdf[self.target_variable].values[:3],
            np.array([[-0.16533269, -0.0223633,  0.02246693]]).T,
            atol=self.atol,
            rtol=self.rtol,
        )

    def test_tail(self, projection_netcdf):
        """Test tail of variable array"""
        npt.assert_allclose(
            projection_netcdf[self.target_variable].values[-3:],
            np.array([[-0.59789735, -0.10988867, np.nan]]).T,
            atol=self.atol,
            rtol=self.rtol,
        )


class TestDdseasonaltasmax:
    """Test netCDF output 'ddseasonaltasmax' variable
    """

    target_variable = "ddseasonaltasmax"
    atol = 1e-4
    rtol = 0

    def test_shape(self, projection_netcdf):
        """Test variable array shape"""
        assert projection_netcdf[self.target_variable].values.shape == (118, 1)

    def test_head(self, projection_netcdf):
        """Test head of variable array"""
        npt.assert_allclose(
            projection_netcdf[self.target_variable].values[:3],
            np.array([[-0.04894612, -0.03128264, -0.02922709]]).T,
            atol=self.atol,
            rtol=self.rtol,
        )

    def test_tail(self, projection_netcdf):
        """Test tail of variable array"""
        npt.assert_allclose(
            projection_netcdf[self.target_variable].values[-3:],
            np.array([[-0.08493597, -0.06603191, np.nan]]).T,
            atol=self.atol,
            rtol=self.rtol,
        )



class TestDdseasonalpr:
    """Test netCDF output 'ddseasonalpr' variable
    """

    target_variable = "ddseasonalpr"
    atol = 1e-4
    rtol = 0

    def test_shape(self, projection_netcdf):
        """Test variable array shape"""
        assert projection_netcdf[self.target_variable].values.shape == (118, 1)

    def test_head(self, projection_netcdf):
        """Test head of variable array"""
        npt.assert_allclose(
            projection_netcdf[self.target_variable].values[:3],
            np.array([[0.00524488, 0.00486552, 0.00480848]]).T,
            atol=self.atol,
            rtol=self.rtol,
        )

    def test_tail(self, projection_netcdf):
        """Test tail of variable array"""
        npt.assert_allclose(
            projection_netcdf[self.target_variable].values[-3:],
            np.array([[0.01309601, 0.01345166, np.nan]]).T,
            atol=self.atol,
            rtol=self.rtol,
        )
