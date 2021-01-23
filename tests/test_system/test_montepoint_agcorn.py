"""System smoke tests for one iteration of a pseudo-Monte Carlo run for Agriculture (corn).

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

RUN_BASENAME = "corn_global_t-tbar_pbar_lnincbr_ir_tp_binp-tbar_pbar_lnincbr_ir_tp_fe-A1TT_A0Y_clus-A1_A0Y_TINV-191220"
RUN_CONFIGS = {
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
        RUN_BASENAME: {"seed-csvv": 123},
        "histclim": {"seed-yearorder": 123},
    },
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
                    "AuxiliaryResult": [
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
                    "AuxiliaryResult": [
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
    expected = {
        RUN_BASENAME: {"seed-csvv": 123},
        "FD_FGLS_inter_climGMFD_Exclude_all-issues_break2_semi-parametric_poly2_OTHERIND_other_energy_TINV_clim_income_spline_lininter": {
            "seed-csvv": 123
        },
        "histclim": {"seed-yearorder": 123},
    }
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
    atol = 0
    rtol = 1e-7

    @pytest.mark.parametrize(
        "result_file", [("base_ds"), ("noadapt_ds"), ("incadapt_ds"), ("histclim_ds"),]
    )
    def test_shape(self, projection_payload, result_file):
        """Test variable array shape"""
        projection_netcdf = getattr(projection_payload, result_file)
        assert projection_netcdf[self.target_variable].values.shape == (118, 1)

    @pytest.mark.parametrize(
        "result_file,expected",
        [
            ("base_ds", np.array([[-80987.25, -60430.58, -12399.255]]).T),
            ("noadapt_ds", np.array([[-80987.25, -60430.58, -12399.255]]).T),
            ("incadapt_ds", np.array([[-80987.25, -60430.58, -12399.255]]).T),
            ("histclim_ds", np.array([[-58008.15, 33512.36, -47440.41]]).T),
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
            ("base_ds", np.array([[-43783.42, 93305.3, -31518.95]]).T),
            ("noadapt_ds", np.array([[-49961.56, 78332.21, -40562.645]]).T),
            ("incadapt_ds", np.array([[-49961.16, 78333.27, -40562.316]]).T),
            ("histclim_ds", np.array([[-43051.676, -529.0065, 18288.943]]).T),
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


class TestResponse:
    """Test netCDF output 'response' variable
    """

    target_variable = "response"
    atol = 0
    rtol = 1e-05

    @pytest.mark.parametrize(
        "result_file", [("base_ds"), ("noadapt_ds"), ("incadapt_ds"), ("histclim_ds"),]
    )
    def test_shape(self, projection_payload, result_file):
        """Test variable array shape"""
        projection_netcdf = getattr(projection_payload, result_file)
        assert projection_netcdf[self.target_variable].values.shape == (118, 1)

    @pytest.mark.parametrize(
        "result_file,expected",
        [
            ("base_ds", np.array([[-4.789829e-4, 1.289884e-3, 1.649605e-3]]).T),
            ("noadapt_ds", np.array([[-4.789829e-4, 1.289884e-3, 1.649605e-3]]).T),
            ("incadapt_ds", np.array([[-4.789829e-4, 1.289884e-3, 1.649605e-3]]).T),
            ("histclim_ds", np.array([[-0.0004739001742564142, 0.0015039884019643068, -0.0003924719349015504]]).T),
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
            ("base_ds", np.array([[-4.457325e-2, -1.660825e-2, -3.079309e-2]]).T),
            ("noadapt_ds", np.array([[-0.041029, -0.015506, -0.027704]]).T),
            ("incadapt_ds", np.array([[-0.041042, -0.015511, -0.027713]]).T),
            ("histclim_ds", np.array([[0.0002463048149365932, 0.001474292599596083, 0.001260366290807724]]).T),
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


class TestResponse2:
    """Test netCDF output 'response2' variable
    """

    target_variable = "response2"
    atol = 0
    rtol = 1e-07

    @pytest.mark.parametrize(
        "result_file", [("base_ds"), ("noadapt_ds"), ("incadapt_ds"), ("histclim_ds"),]
    )
    def test_shape(self, projection_payload, result_file):
        """Test variable array shape"""
        projection_netcdf = getattr(projection_payload, result_file)
        assert projection_netcdf[self.target_variable].values.shape == (118, 1)

    @pytest.mark.parametrize(
        "result_file,expected",
        [
            ("base_ds", np.array([[35549.101562, 56105.773438, 104137.093750]]).T),
            ("noadapt_ds", np.array([[35549.101562, 56105.773438, 104137.093750]]).T),
            ("incadapt_ds", np.array([[35549.101562, 56105.773438, 104137.093750]]).T),
            ("histclim_ds", np.array([[35143.507812, 126664.015625, 45711.242188]]).T),
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
            ("base_ds", np.array([[72752.976562, 209841.671875, 85017.429688]]).T),
            ("noadapt_ds", np.array([[66574.828125, 194868.578125, 75973.734375]]).T),
            ("incadapt_ds", np.array([[66575.234375, 194869.640625, 75974.062500]]).T),
            ("histclim_ds", np.array([[50099.980469, 92622.648438, 111440.593750]]).T),
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


class TestDdseasonalpr:
    """Test netCDF output 'ddseasonalpr' variable
    """

    target_variable = "ddseasonalpr"
    atol = 0
    rtol = 1e-07

    @pytest.mark.parametrize(
        "result_file", [("base_ds"), ("histclim_ds"),]  # Don't need to test adapt files if aux variable.
    )
    def test_shape(self, projection_payload, result_file):
        """Test variable array shape"""
        projection_netcdf = getattr(projection_payload, result_file)
        assert projection_netcdf[self.target_variable].values.shape == (118, 1)

    @pytest.mark.parametrize(
        "result_file,expected",
        [
            ("base_ds", np.array([[381.588989, 600.228821, 1116.934204]]).T),
            ("histclim_ds", np.array([[374.481415, 1349.177002, 486.706604]]).T),
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
            ("base_ds", np.array([[868.864319, 2551.123291, 991.761536]]).T),
            ("histclim_ds", np.array([[584.754822, 1096.474976, 1306.258057]]).T),
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


class TestDdseasonaltasmax:
    """Test netCDF output 'ddseasonaltasmax' variable
    """

    target_variable = "ddseasonaltasmax"
    atol = 0
    rtol = 1e-07

    @pytest.mark.parametrize(
        "result_file", [("base_ds"), ("histclim_ds"),]  # Don't need to test adapt files if aux variable.
    )
    def test_shape(self, projection_payload, result_file):
        """Test variable array shape"""
        projection_netcdf = getattr(projection_payload, result_file)
        assert projection_netcdf[self.target_variable].values.shape == (118, 1)

    @pytest.mark.parametrize(
        "result_file,expected",
        [
            ("base_ds", np.array([[1439.603882, 2260.348389, 4211.435547]]).T),
            ("histclim_ds", np.array([[1450.193848, 5220.333496, 1884.740845]]).T),
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
            ("base_ds", np.array([[2425.036133, 6968.686035, 2823.600342]]).T),
            ("histclim_ds", np.array([[2074.002686, 3815.721436, 4606.115723]]).T),
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
