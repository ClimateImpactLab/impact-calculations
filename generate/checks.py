from netCDF4 import Dataset
import numpy as np

do_skip_check = False


def check_result_100years(filepath, variable='rebased', regioncount=24378):
    if do_skip_check:
        return True

    try:
        rootgrp = Dataset(filepath, 'r', format='NETCDF4')
        values = rootgrp.variables[variable][:, :]
        rootgrp.close()
        
        if values.shape[0] < 100 or values.shape[1] < regioncount:
            return False

        if np.ma.getmask(values) and values.mask[100, int(regioncount / 2)]:
            return False

        if np.isnan(values[100, int(regioncount / 2)]) or np.all(np.logical_or(values[100, :] == 0, np.logical_or(values[100, :] == 1, np.isnan(values[100, :])))):
            return False

        return True
    except Exception as ex:
        print("Exception raised but returning anyways:")
        print(ex)
        return False
