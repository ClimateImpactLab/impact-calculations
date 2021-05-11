import numpy as np
import xarray as xr
from climate.netcdfs import load_netcdf


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
