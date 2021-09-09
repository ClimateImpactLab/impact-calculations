"""System smoke tests for one iteration Monte Carlo run for the labor sector.

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

from utils import tmpdir_projection


pytestmark = pytest.mark.imperics_shareddir

RUN_BASENAME = "combined_uninteracted_spline_empshare_noFE"
RUN_CONFIGS = {
    "filter-region": "USA.14.608",
    "mc-n": 1,
    "pvals": {RUN_BASENAME: {"seed-csvv": 123}, "histclim": {"seed-yearorder": 123},},
    "mode": "montecarlo",
    "do_historical": True,
    "do_farmers": True,
    "only-models": ["CCSM4"],
    "only-ssp": "SSP3",
    "only-rcp": "rcp85",
    "only-iam": "low",
    "climcovar": {"class": "mean", "length": 30},
    "econcovar": {"class": "mean", "length": 30},
    "timerate": "day",
    "climate": [
        "tasmax",
        "tasmax_rcspline",
        "tas",
        "tas-poly-2",
        "tas-poly-3",
        "tas-poly-4",
    ],
    "models": [
        {
            "csvvs": "social/parameters/labor/post_replication/combined_uninteracted_spline_empshare_noFE.csvv",
            "covariates": [
                "loggdppc",
                "climtasmax",
                "climtas",
                "climtas-poly-2",
                "climtas-poly-3",
                "climtas-poly-4",
            ],
            "knots": [27, 37, 39],
            "description": "labor productivity",
            "specifications": {
                "minlost_lo": {
                    "csvv-subset": [0, 2],
                    "csvv-reunit": [
                        {
                            "variable": "outcome",
                            "new-unit": "minutes worked by individual",
                        }
                    ],
                    "description": "low-risk labor productivity",
                    "indepunit": "C",
                    "depenunit": "minutes worked by individual",
                    "functionalform": "cubicspline",
                    "prefix": "tasmax_rcspline",
                    "variable": "tasmax",
                },
                "minlost_hi": {
                    "csvv-subset": [2, 4],
                    "csvv-reunit": [
                        {
                            "variable": "outcome",
                            "new-unit": "minutes worked by individual",
                        }
                    ],
                    "indepunit": "C",
                    "depenunit": "minutes worked by individual",
                    "description": "high-risk labor productivity",
                    "functionalform": "cubicspline",
                    "prefix": "tasmax_rcspline",
                    "variable": "tasmax",
                },
                "riskshare_hi": {
                    "csvv-subset": [4, 10],
                    "csvv-reunit": [{"variable": "outcome", "new-unit": "unitless"}],
                    "indepunit": "C",
                    "depenunit": "unitless",
                    "description": "share of high-risk labor",
                    "functionalform": "coefficients",
                    "variables": ["1 [scalar]"],
                },
            },
            "calculation": [
                {
                    "FractionSum": [
                        {"YearlyAverageDay": {"model": "minlost_hi"}},
                        {
                            "Clip": [
                                {"YearlyAverageDay": {"model": "riskshare_hi"}},
                                0.046444122,
                                0.99408281,
                            ]
                        },
                        {"YearlyAverageDay": {"model": "minlost_lo"}},
                    ]
                },
                "Rebase",
            ],
        }
    ],
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
    with tmpdir_projection(RUN_CONFIGS, "montecarlo labor test") as tmpdirname:
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
    atol = 1e-6
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
            ("base_ds", np.array([[-0.049367, 0.017414, 0.086386]]).T),
            ("noadapt_ds", np.array([[-0.049367, 0.017414, 0.086386]]).T),
            ("incadapt_ds", np.array([[-0.049367, 0.017414, 0.086386]]).T),
            ("histclim_ds", np.array([[-0.052995, 0.006918, -0.082769]]).T),
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
            ("base_ds", np.array([[-0.718501, -0.663922, -0.475]]).T),
            ("noadapt_ds", np.array([[-0.779091, -0.616543, -0.384347]]).T),
            ("incadapt_ds", np.array([[-0.721431, -0.661693, -0.47032]]).T),
            ("histclim_ds", np.array([[-0.11957, -0.057036, -0.154594]]).T),
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
