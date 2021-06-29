from netCDF4 import Dataset
import numpy as np

do_skip_check = False


def check_result_100years(filepath, variable='rebased', regioncount=24378):
    """validates the values and dimensions of a two dimensional netcdf4 file containing a specified variable -- 
    for example a region by year netcdf4 file but there is no requirement regarding the name of the dimensions.

    - The dimension sizes are checked. It is expected that the size of the first dimension is at least 100 and the size of the second dimension
    can be passed as a parameter.
    - The values of a specified variable are checked. The variable is validated if
        - an arbitrary value is not missing and
        - an arbitrary slice from the first dimension doesn't contain only zero values
        - an arbitrary slice from the first dimension doesn't contain only values equal to one
        - an arbitrary slice from the first dimension doesn't contain only 'nan' values

    Parameters
    ----------
    filepath : str
        full absolute path to a netcdf4 file. 
    variable : str
        variable of which the values are used for validation
    regioncount : int
        expected size of the region dimension 

    Returns
    -------
    boolean, True if the validation succeeded.
    """
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

        if np.all(np.logical_or(values[100, :] == 0, np.logical_or(values[100, :] == 1, np.isnan(values[100, :])))):
            return False

        return True
    except Exception as ex:
        # Any failure here is a successful check giving a negative result (that is, the file needs to be regenerated)
        return False
