"""System smoke tests for one iteration of a pseudo-Monte Carlo run for the energy sector.

These tests are "pseudo-Monte Carlo" because we mask out the random number 
generator (RNG) when drawing from a multivariate-normal (MVN) distribution, 
roughly simulating a Monte Carlo draw. We need to do this because we cannot 
get stable MVN draws by simply seeding the RNG. The actual MVN draw is 
numerically like a "point-estimate" projection run posing as a Monte Carlo
run.

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


RUN_BASENAME = "FD_FGLS_inter_climGMFD_Exclude_all-issues_break2_semi-parametric_poly2_OTHERIND_other_energy_TINV_clim_income_spline_lininter"
RUN_CONFIGS = {
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
    "timerate": "year",
    "climate": [
        "tas",
        "tas-poly-2",
        "tas-cdd-20",
        "tas-cdd-20-poly-2",
        "tas-hdd-20",
        "tas-hdd-20-poly-2",
    ],
    "models": [
        {
            "csvvs": "social/parameters/energy/projectionT/*.csvv",
            "covariates": [
                {
                    "incbin": [
                        "-inf",
                        7.246,
                        7.713,
                        8.136,
                        8.475,
                        8.776,
                        9.087,
                        9.385,
                        9.783,
                        10.198,
                        "inf",
                    ]
                },
                {
                    "year*incbin": [
                        "-inf",
                        7.246,
                        7.713,
                        8.136,
                        8.475,
                        8.776,
                        9.087,
                        9.385,
                        9.783,
                        10.198,
                        "inf",
                    ]
                },
                "climtas-cdd-20",
                "climtas-hdd-20",
                {
                    "climtas-cdd-20*incbin": [
                        "-inf",
                        7.246,
                        7.713,
                        8.136,
                        8.475,
                        8.776,
                        9.087,
                        9.385,
                        9.783,
                        10.198,
                        "inf",
                    ]
                },
                {
                    "climtas-hdd-20*incbin": [
                        "-inf",
                        7.246,
                        7.713,
                        8.136,
                        8.475,
                        8.776,
                        9.087,
                        9.385,
                        9.783,
                        10.198,
                        "inf",
                    ]
                },
                {
                    "loggdppc-shifted*incbin": [
                        "-inf",
                        7.246,
                        7.713,
                        8.136,
                        8.475,
                        8.776,
                        9.087,
                        9.385,
                        9.783,
                        10.198,
                        "inf",
                    ]
                },
                {
                    "loggdppc-shifted*year*incbin": [
                        "-inf",
                        7.246,
                        7.713,
                        8.136,
                        8.475,
                        8.776,
                        9.087,
                        9.385,
                        9.783,
                        10.198,
                        "inf",
                    ]
                },
            ],
            "clipping": False,
            "description": "Change in energy usage driven by a single day's mean temperature",
            "depenunit": "kWh/pc",
            "specifications": {
                "tas": {
                    "description": "Uninteracted term.",
                    "indepunit": "C",
                    "functionalform": "polynomial",
                    "variable": "tas",
                },
                "hdd-20": {
                    "description": "Below 20C days.",
                    "indepunit": "C",
                    "functionalform": "polynomial",
                    "variable": "tas-hdd-20",
                },
                "cdd-20": {
                    "description": "Above 20C days.",
                    "indepunit": "C",
                    "functionalform": "polynomial",
                    "variable": "tas-cdd-20",
                },
            },
            "calculation": [
                {
                    "Sum": [
                        {"YearlyApply": {"model": "tas"}},
                        {"YearlyApply": {"model": "hdd-20"}},
                        {"YearlyApply": {"model": "cdd-20"}},
                    ]
                },
                "Rebase",
            ],
        }
    ],
}


@pytest.fixture(scope="module")
def projection_payload(static_mvn):
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
            results_pvals = yaml.safe_load(fl)

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
    atol = 0
    rtol = 1e-7

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
            ("base_ds", np.array([[423.7772, -1107.7778, -1281.3613]]).T),
            ("noadapt_ds", np.array([[423.7772, -1107.7778, -1281.3613]]).T),
            ("incadapt_ds", np.array([[423.7772, -1107.7778, -1281.3613]]).T),
            ("histclim_ds", np.array([[540.6629, -122.77686, 113.05155]]).T),
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
            ("base_ds", np.array([[-323332.72, -340289.84, -310093.56]]).T),
            ("noadapt_ds", np.array([[4506.751, 3234.8323, 4155.759]]).T),
            ("incadapt_ds", np.array([[-317618.66, -335153.22, -303467.62]]).T),
            ("histclim_ds", np.array([[-218661.08, -178848.5, -219527.86]]).T),
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
