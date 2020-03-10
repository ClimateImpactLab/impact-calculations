"""System smoke tests for one iteration Monte Carlo run for Agriculture (corn).

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


RUN_BASENAME = "corn_global_t-tbar_pbar_lnincbr_ir_tp_binp-tbar_pbar_lnincbr_ir_tp_fe-A1TT_A0Y_clus-A1_A0Y_TINV-191220"
RUN_CONFIGS = {
    "module": "tests/configs/corn_prsplitmodel_partiald.yml",
    "filter-region": "USA.14.608",
    "mode": "montecarlo",
    "do_farmers": True,
    "only-models": ["CCSM4"],
    "only-ssp": "SSP3",
    "only-rcp": "rcp85",
    "only-iam": "low",
    "mc-n": 1,
    "pvals": {
        "FD_FGLS_inter_climGMFD_Exclude_all-issues_break2_semi-parametric_poly2_OTHERIND_other_energy_TINV_clim_income_spline_lininter": {
            "seed-csvv": 123
        },
        RUN_BASENAME: {
            "seed-csvv": 123
        },
        "histclim": {"seed-yearorder": 123},
    }
}


@pytest.fixture(scope="module")
def projection_payload():
    """Run the projection in tmpdir, get McResults namedtuple from output, clean output on exit
    """
    # Read output files from projection into named tuple of xr.Datasets and dicts.
    # Tests read in named tuple instances.
    McResults = namedtuple("McResults", ["base_ds", "noadapt_ds", "incadapt_ds", "histclim_ds", "pvals_dict"])

    # Trigger projection run in temprary directory:
    with tmpdir_projection(RUN_CONFIGS, "montecarlo energy test") as tmpdirname:
        resultsdir = Path(tmpdirname, "batch0/rcp85/CCSM4/low/SSP3")

        with open(Path(resultsdir, "pvals.yml")) as fl:
            results_pvals = yaml.load(fl, Loader=yaml.SafeLoader)

        test_payload = McResults(
            base_ds=xr.open_dataset(Path(resultsdir, f"{RUN_BASENAME}.nc4")),
            noadapt_ds=xr.open_dataset(Path(resultsdir, f"{RUN_BASENAME}-noadapt.nc4")),
            incadapt_ds=xr.open_dataset(Path(resultsdir, f"{RUN_BASENAME}-incadapt.nc4")),
            histclim_ds=xr.open_dataset(Path(resultsdir, f"{RUN_BASENAME}-histclim.nc4")),
            pvals_dict=results_pvals,
        )
        yield test_payload


def test_pvals(projection_payload):
    expected = {
        RUN_BASENAME: {'seed-csvv': 123}, 
        'FD_FGLS_inter_climGMFD_Exclude_all-issues_break2_semi-parametric_poly2_OTHERIND_other_energy_TINV_clim_income_spline_lininter': {
            'seed-csvv': 123
        },
        'histclim': {'seed-yearorder': 123}
    }
    assert projection_payload.pvals_dict == expected


@pytest.mark.parametrize("result_file", [
    ("base_ds"),
    ("noadapt_ds"),
    ("incadapt_ds"),
    ("histclim_ds"),
])
def test_region(projection_payload, result_file):
    """Test the 'regions' dimension of output netCDF
    """
    projection_netcdf = getattr(projection_payload, result_file)
    assert str(projection_netcdf["regions"].values.item()) == "USA.14.608"


@pytest.mark.parametrize("result_file", [
    ("base_ds"),
    ("noadapt_ds"),
    ("incadapt_ds"),
    ("histclim_ds"),
])
class TestYear:
    """Test netCDF output 'year' dimension
    """
    target_variable = "year"

    def test_shape(self, projection_payload, result_file):
        """Test variable array shape"""
        projection_netcdf = getattr(projection_payload, result_file)
        assert projection_netcdf[self.target_variable].values.shape == (118,)

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
            np.array([2096, 2097, 2098]),
        )


class TestRebased:
    """Test netCDF output 'rebased' variable
    """
    target_variable = "rebased"
    atol = 1
    rtol = 0

    @pytest.mark.parametrize("result_file", [
        ("base_ds"),
        ("noadapt_ds"),
        ("incadapt_ds"),
        ("histclim_ds"),
    ])
    def test_shape(self, projection_payload, result_file):
        """Test variable array shape"""
        projection_netcdf = getattr(projection_payload, result_file)
        assert projection_netcdf[self.target_variable].values.shape == (118, 1)

    @pytest.mark.parametrize("result_file,expected", [
        ("base_ds", np.array([18437142.0, 15240259.0, 13820419.0])),
        ("noadapt_ds", np.array([18437142.0, 15240259.0, 13820419.0])),
        ("incadapt_ds", np.array([18437142.0, 15240259.0, 13820419.0])),
        ("histclim_ds", np.array([-2261668.0,  3017162.0, 3017162.0])),
    ])
    def test_head(self, projection_payload, result_file, expected):
        """Test head of variable array"""
        projection_netcdf = getattr(projection_payload, result_file)
        npt.assert_allclose(
            projection_netcdf[self.target_variable].values[:3],
            expected,
            atol=self.atol,
            rtol=self.rtol,
        )

    @pytest.mark.parametrize("result_file,expected", [
        ("base_ds", np.array([18277254.0, -23021556.0, np.nan])),
        ("noadapt_ds", np.array([18388806.0, -21105998.0, np.nan])),
        ("incadapt_ds", np.array([18388806.0, -21105956.0, np.nan])),
        ("histclim_ds", np.array([ 2662714.8, -6997009.5, np.nan])),
    ])
    def test_tail(self, projection_payload, result_file, expected):
        """Test tail of variable array"""
        projection_netcdf = getattr(projection_payload, result_file)
        npt.assert_allclose(
            projection_netcdf[self.target_variable].values[-3:],
            expected,
            atol=self.atol,
            rtol=self.rtol,
        )
