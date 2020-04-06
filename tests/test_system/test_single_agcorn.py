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

from utils import tmpdir_projection


pytestmark = pytest.mark.imperics_shareddir


@pytest.fixture(scope="module")
def projection_netcdf():
    """Runs the projection in tmpdir, gets results netCDF, cleans output on exit
    """
    run_configs = {
        "mode": "writecalcs",
        "singledir": "single",
        "filter-region": "USA.14.608",
        "do_farmers": False,
        "do_historical": False,
        "deltamethod": False,
        "climate": ["tasmax", "edd", "pr", "pr-poly-2 = pr-monthsum-poly-2"],
        "grid-weight": "cropwt",
        "models": [
            {
                "calculation": [
                    {
                        "Sum": [
                            {"YearlySumIrregular": {"model": "gddkdd"}},
                            {"YearlySumIrregular": {"model": "precip"}},
                        ]
                    },
                    {
                        "AuxillaryResult": [
                            {
                                "PartialDerivative": {
                                    "covariate": "seasonaltasmax",
                                    "covarunit": "C",
                                }
                            },
                            "ddseasonaltasmax",
                        ]
                    },
                    {
                        "AuxillaryResult": [
                            {
                                "PartialDerivative": {
                                    "covariate": "seasonalpr",
                                    "covarunit": "mm",
                                }
                            },
                            "ddseasonalpr",
                        ]
                    },
                    "Rebase",
                    "Exponentiate",
                    {
                        "KeepOnly": [
                            "ddseasonaltasmax",
                            "ddseasonalpr",
                            "rebased",
                            "response",
                            "response2",
                        ]
                    },
                ],
                "clipping": False,
                "covariates": [
                    "loggdppc",
                    "seasonaltasmax",
                    "seasonalpr",
                    "ir-share",
                    "seasonaltasmax*seasonalpr",
                ],
                "csvvs": "social/parameters/agriculture/corn/corn_global_t-tbar_pbar_lnincbr_ir_tp_binp-tbar_pbar_lnincbr_ir_tp_fe-A1TT_A0Y_clus-A1_A0Y_TINV-191220.csvv",
                "description": "Yield rate for corn",
                "specifications": {
                    "gddkdd": {
                        "beta-limits": {"kdd-31": "-inf, 0"},
                        "depenunit": "log kg / Ha",
                        "description": "Temperature-driven " "yield rate for corn",
                        "functionalform": "coefficients",
                        "variables": {
                            "gdd-8-31": "edd.bin(8) " "- " "edd.bin(31) " "[C day]",
                            "kdd-31": "edd.bin(31) " "[C day]",
                        },
                    },
                    "precip": {
                        "depenunit": "log kg / Ha",
                        "description": "Precipitation-driven " "yield rate for corn",
                        "functionalform": "sum-by-time",
                        "indepunit": "mm",
                        "subspec": {"functionalform": "polynomial", "variable": "pr"},
                        "suffixes": [1, 2, 3, 4, 5, 6, 7, 8, 9, "r", "r", "r"],
                    },
                },
                "within-season": "social/baselines/agriculture/world-combo-201710-growing-seasons-corn-1stseason.csv",
            }
        ],
        "rolling-years": 2,
        "timerate": "month",
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
            np.array([[-0.15186098, -0.02401909, 0.01957218]]).T,
            atol=self.atol,
            rtol=self.rtol,
        )

    def test_tail(self, projection_netcdf):
        """Test tail of variable array"""
        npt.assert_allclose(
            projection_netcdf[self.target_variable].values[-3:],
            np.array([[-0.6244463, -0.13643758, np.nan]]).T,
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
            np.array([[-0.05384747, -0.03535344, -0.03308476]]).T,
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
            np.array([[0.00369034, 0.00358236, 0.00359436]]).T,
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
