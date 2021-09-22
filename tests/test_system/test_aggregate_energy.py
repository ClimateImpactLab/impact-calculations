"""System smoke tests for a single aggregation for the energy sector.

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
from generate.aggregate import main as main_aggregate

pytestmark = pytest.mark.imperics_shareddir


@pytest.fixture(scope="module")
def projection_netcdf():
    """Runs the projection in tmpdir, gets results netCDF, cleans output on exit
    """

    run_configs = {
        'outputdir': '/mnt/sacagawea_shares/gcp/outputs/energy/unittest',
        'basename': 'FD_FGLS_inter_climGMFD_Exclude_all-issues_break2_semi-parametric_poly2_OTHERIND_other_energy_TINV_clim_income_spline-incadapt',
        'levels-weighting': 'social/baselines/energy/IEA_Price_FIN_Clean_gr014_GLOBAL_COMPILE.dta:country:year:other_energycompile_price',
        'levels-unit': '',
        'aggregate-weighting-numerator': 'population * social/baselines/energy/IEA_Price_FIN_Clean_gr014_GLOBAL_COMPILE.dta:country:year:other_energycompile_price',
        'aggregate-weighting-denominator': 'population',
        'aggregated-unit': '',
        'infix': 'withprice'
    }
    
    # Trigger projection run in temporary directory:
    with tmpdir_projection(run_configs, "aggregate energy test", main_aggregate, 'writedir') as tmpdirname:
        results_nc_path = {
            'results_aggregate': Path(
                tmpdirname,
                "median/rcp45/surrogate_CanESM2_89/low/SSP3",
                "FD_FGLS_inter_climGMFD_Exclude_all-issues_break2_semi-parametric_poly2_OTHERIND_other_energy_TINV_clim_income_spline-incadapt-withprice-aggregated.nc4"
            ),
            'results_levels': Path(
                tmpdirname,
                "median/rcp45/surrogate_CanESM2_89/low/SSP3",
                "FD_FGLS_inter_climGMFD_Exclude_all-issues_break2_semi-parametric_poly2_OTHERIND_other_energy_TINV_clim_income_spline-incadapt-withprice-levels.nc4"
                                  )}

        yield {'results_aggregate' : xr.open_dataset(results_nc_path['results_aggregate']), 'results_levels': xr.open_dataset(results_nc_path['results_levels'])}


def test_levels_regions(projection_netcdf):
    """Test regions in *levels results file"""
    actual = projection_netcdf['results_levels']['regions'].values
    assert actual.shape == (24378, )
    assert actual[0] == 'CAN.1.2.28'
    assert actual[-1] == 'BWA.4.13'

def test_levels_rebased(projection_netcdf):
    """Test shape & (head, tail) values of 'rebased' in *levels file"""
    actual = projection_netcdf['results_levels']['rebased'].values

    assert actual.shape == (119, 24378)

    goal_head = np.array([5.39619, 19.44508, 13.45272])
    goal_tail = np.array([-576.1952, -592.8362, -621.2902])
    npt.assert_allclose(actual[:3, 0], goal_head, atol=1e-4, rtol=0)
    npt.assert_allclose(actual[-3:, -1], goal_tail, atol=1e-4, rtol=0)

def test_aggregated_regions(projection_netcdf):
    """Test regions in *aggregated results file"""
    actual = projection_netcdf['results_aggregate']['regions'].values
    assert actual.shape == (5716, )
    assert actual[0] == ''
    assert actual[-1] == 'FUND-JPK'

def test_aggregated_rebased(projection_netcdf):
    """Test shape & (head, tail) values of 'rebased' in *aggregated file"""
    actual = projection_netcdf['results_aggregate']['rebased'].values

    assert actual.shape == (119, 5716)

    goal_head = np.array([2.25789, 1.751476, 1.788347])
    goal_tail = np.array([-264.9955530, -274.8205048, -272.6145703])
    npt.assert_allclose(actual[:3, 0], goal_head, atol=1e-4, rtol=0)
    npt.assert_allclose(actual[-3:, -1], goal_tail, atol=1e-4, rtol=0)

