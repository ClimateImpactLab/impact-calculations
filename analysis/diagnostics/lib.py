"""
Various utils for various sector-specific diagnostic scripts.
"""

from climate.netcdfs import load_netcdf
from autodoc.lib import *
endbaseline = 2015

def get_weather(weathertemplate, years, shapenum, show_all_years=None, variable='tas', regindex='hierid', subset=None):
    if show_all_years is None:
        show_all_years = []

    weather = {}
    for year in years:
        filepath = weathertemplate.format(rcp='historical' if year < 2006 else 'rcp85', variable=variable, year=year)
        assert os.path.exists(filepath), "Cannot find %s" % filepath
        ds = load_netcdf(filepath)
        if isinstance(shapenum, str):
            regions = list(ds[regindex].values)
            shapenum = regions.index(shapenum)
            
        data = ds[variable].isel(**{regindex: shapenum})
        if subset is None:
            data = data.values
        else:
            data = data[subset].values

        if year in show_all_years:
            print((str(year) + ': ' + ','.join(map(str, data))))
        else:
            print((str(year) + ': ' + ','.join(map(str, data[:10])) + '...'))

        weather[year] = data

    return weather

def get_outputs(outputpath, years, shapenum, timevar='year'):
    """Read and subset

    Parameters
    ----------
    outputpath : str
        Path to output projection NetCDF4 file.
    years : sequence of int
        Years to extract from the target file.
    shapenum : str, int, or None, optional
        If str, `shapenum` is treated as a region and this region is extracted
        from the target file. Otherwise, used to extract from the last
        dimension of the data variable.
    timevar : str, optional
        Name of the "time" variable.

    Returns
    -------
    outputs : dict of dicts
        Data extracted from the projection NetCDF4 file. Keys to this dict
        give years (as int) from the file, and values are nested dicts like:
        {variable: value}.
    """
    rootgrp = Dataset(outputpath, 'r', format='NETCDF4')
    if isinstance(shapenum, str):
        regions = list(rootgrp.variables['regions'][:])
        shapenum = regions.index(shapenum)

    outyears = list(rootgrp.variables[timevar])
    outvars = [var for var in rootgrp.variables if len(rootgrp.variables[var].shape) == 2]
    print('year,' + ','.join(outvars))
    
    outputs = {}
    for year in years:
        data = {var: rootgrp.variables[var][outyears.index(year), shapenum] for var in outvars}
        outputs[year] = data
        
        print(','.join([str(year)] + [str(data[var]) for var in outvars]))

    return outputs
