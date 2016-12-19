from netCDF4 import Dataset
import numpy as np

def check_result_100years(filepath, variable='rebased'):
    rootgrp = Dataset(filepath, 'r', format='NETCDF4')
    values = rootgrp.variables[variable][:, :]

    if values.shape[0] < 100 or values.shape[1] < 20000:
        return False

    if np.isnan(values[100, 10000]):
        return False

    return True
