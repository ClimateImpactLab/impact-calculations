from netCDF4 import Dataset
import numpy as np

def check_result_100years(filepath, variable='rebased'):
    try:
        rootgrp = Dataset(filepath, 'r', format='NETCDF4')
        values = rootgrp.variables[variable][:, :]

        if values.shape[0] < 100 or values.shape[1] < 20000:
            return False

        if np.isnan(values[100, 10000]) or np.all(values[100, :] == 0):
            return False

        return True
    except:
        return False
