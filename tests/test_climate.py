import numpy as np
import xarray as xr
from climate.netcdfs import load_netcdf
from climate import discover
import pytest 

def test_load_netcdf(tmpdir):
    """Test that load_netcdf actually loads a dataset."""
    # Build data. Dump it to tmp netcdf4 file.
    testdata_path = tmpdir.join("test.nc")
    orig_ds = xr.Dataset(
        {"a_variable": (["time"], np.array([11, 12, 13]))},
        coords={"time": np.array([1, 2, 3])},
    )
    orig_ds.to_netcdf(testdata_path)

    # This is the actual, very sophisticated test:
    ds = load_netcdf(testdata_path)
    assert ds == orig_ds


@pytest.mark.imperics_shareddir
def test_standard_variable_identifies():

    """ testing that discover.standard_variable() is able to find existing data """

    # particular version of tas data with month timerate 
    discover.standard_variable('tasmin = tasmin-clip23', 'month', **{'grid-weight': 'cropwt'})