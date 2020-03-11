"""System smoke tests for one iteration Monte Carlo run for the energy sector.

These will likely fail if run as installed package as we unfortunately make
strong assumptions about directory structure. These are also smoke tests,
and are not comprehensive.
"""

from pathlib import Path
from collections import namedtuple

import pytest
import yaml
import xarray as xr
import numpy as np
import numpy.testing as npt

from generate.generate import tmpdir_projection


pytestmark = pytest.mark.imperics_shareddir


RUN_BASENAME = "FD_FGLS_inter_climGMFD_Exclude_all-issues_break2_semi-parametric_poly2_OTHERIND_other_energy_TINV_clim_income_spline_lininter"
RUN_CONFIGS = {
    "module": "impacts/energy/hddcddspline_t_OTHERIND_other_energy.yml",
    "filter-region": "USA.14.608",
    "mode": "montecarlo",
    "do_farmers": True,
    "do_only": "interpolation",
    "only-models": ["CCSM4"],
    "only-ssp": "SSP3",
    "only-rcp": "rcp85",
    "only-iam": "low",
    "econcovar": {"class": "mean", "length": 15},
    "climcovar": {"class": "mean", "length": 15},
    "loggdppc-delta": 9.087,
    "mc-n": 1,
    "pvals": {RUN_BASENAME: {"seed-csvv": 123}, "histclim": {"seed-yearorder": 123},},
}


@pytest.fixture(scope="module")
def projection_payload():
    """Run the projection in tmpdir, get McResults namedtuple from output, clean output on exit
    """
    # Read output files from projection into named tuple of xr.Datasets and dicts.
    # Tests read in named tuple instances.
    McResults = namedtuple(
        "McResults",
        ["base_ds", "noadapt_ds", "incadapt_ds", "histclim_ds", "pvals_dict"],
    )

    # Trigger projection run in temprary directory:
    with tmpdir_projection(RUN_CONFIGS, "montecarlo energy test") as tmpdirname:
        resultsdir = Path(tmpdirname, "batch0/rcp85/CCSM4/low/SSP3")

        with open(Path(resultsdir, "pvals.yml")) as fl:
            results_pvals = yaml.load(fl, Loader=yaml.SafeLoader)

        test_payload = McResults(
            base_ds=xr.open_dataset(Path(resultsdir, f"{RUN_BASENAME}.nc4")),
            noadapt_ds=xr.open_dataset(Path(resultsdir, f"{RUN_BASENAME}-noadapt.nc4")),
            incadapt_ds=xr.open_dataset(
                Path(resultsdir, f"{RUN_BASENAME}-incadapt.nc4")
            ),
            histclim_ds=xr.open_dataset(
                Path(resultsdir, f"{RUN_BASENAME}-histclim.nc4")
            ),
            pvals_dict=results_pvals,
        )
        yield test_payload


def test_pvals(projection_payload):
    expected = {RUN_BASENAME: {"seed-csvv": 123}, "histclim": {"seed-yearorder": 123}}
    assert projection_payload.pvals_dict == expected


@pytest.mark.parametrize(
    "result_file", [("base_ds"), ("noadapt_ds"), ("incadapt_ds"), ("histclim_ds"),]
)
def test_region(projection_payload, result_file):
    """Test the 'regions' dimension of output netCDF
    """
    projection_netcdf = getattr(projection_payload, result_file)
    assert str(projection_netcdf["regions"].values.item()) == "USA.14.608"


@pytest.mark.parametrize(
    "result_file", [("base_ds"), ("noadapt_ds"), ("incadapt_ds"), ("histclim_ds"),]
)
class TestYear:
    """Test netCDF output 'year' dimension
    """

    target_variable = "year"

    def test_shape(self, projection_payload, result_file):
        """Test variable array shape"""
        projection_netcdf = getattr(projection_payload, result_file)
        assert projection_netcdf[self.target_variable].values.shape == (120,)

    def test_head(self, projection_payload, result_file):
        """Test head of variable array"""
        projection_netcdf = getattr(projection_payload, result_file)
        npt.assert_array_equal(
            projection_netcdf[self.target_variable].values[:3],
            np.array([1981, 1982, 1983]),
        )

    def test_tail(self, projection_payload, result_file):
        """Test tail of variable array"""
        projection_netcdf = getattr(projection_payload, result_file)
        npt.assert_array_equal(
            projection_netcdf[self.target_variable].values[-3:],
            np.array([2098, 2099, 2100]),
        )


class TestRebased:
    """Test netCDF output 'rebased' variable
    """

    target_variable = "rebased"
    atol = 1e-4
    rtol = 0

    @pytest.mark.parametrize(
        "result_file", [("base_ds"), ("noadapt_ds"), ("incadapt_ds"), ("histclim_ds"),]
    )
    def test_shape(self, projection_payload, result_file):
        """Test variable array shape"""
        projection_netcdf = getattr(projection_payload, result_file)
        assert projection_netcdf[self.target_variable].values.shape == (120, 1)

    @pytest.mark.parametrize(
        "result_file,expected",
        [
            ("base_ds", np.array([[182.74854, 138.99937, 432.08884]]).T),
            ("noadapt_ds", np.array([[182.74854, 138.99937, 432.08884]]).T),
            ("incadapt_ds", np.array([[182.74854, 138.99937, 432.08884]]).T),
            ("histclim_ds", np.array([[463.31558, 320.79092, 320.79092]]).T),
        ],
    )
    def test_head(self, projection_payload, result_file, expected):
        """Test head of variable array"""
        projection_netcdf = getattr(projection_payload, result_file)
        npt.assert_allclose(
            projection_netcdf[self.target_variable].values[:3],
            expected,
            atol=self.atol,
            rtol=self.rtol,
        )

    @pytest.mark.parametrize(
        "result_file,expected",
        [
            ("base_ds", np.array([[4340.6616, 3850.7495, 3353.314]]).T),
            ("noadapt_ds", np.array([[2130.226, 1964.3873, 1609.678]]).T),
            ("incadapt_ds", np.array([[4839.495, 4291.672, 3885.245]]).T),
            ("histclim_ds", np.array([[598.6438, 1263.2665, 689.26575]]).T),
        ],
    )
    def test_tail(self, projection_payload, result_file, expected):
        """Test tail of variable array"""
        projection_netcdf = getattr(projection_payload, result_file)
        npt.assert_allclose(
            projection_netcdf[self.target_variable].values[-3:],
            expected,
            atol=self.atol,
            rtol=self.rtol,
        )
