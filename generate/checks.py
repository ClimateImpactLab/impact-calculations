from netCDF4 import Dataset
import numpy as np

def check_result_100years(filepath, variable='rebased', regioncount=24378):
    try:
        rootgrp = Dataset(filepath, 'r', format='NETCDF4')
        values = rootgrp.variables[variable][:, :]

        if values.shape[0] < 100 or values.shape[1] < regioncount:
            return False

        if hasattr(values, 'mask') and values.mask[100, regioncount / 2]:
            return False

        if np.isnan(values[100, regioncount / 2]) or np.all(np.logical_or(values[100, :] == 0, np.logical_or(values[100, :] == 1, np.isnan(values[100, :])))):
            return False

        return True
    except:
        return False
