"""Helper functions for writing our NetCDF4 files."""

import os
import numpy as np
from netCDF4 import Dataset

def create(targetdir, basename):
    """Create a blank NetCDF4 file, at `<targetdir>/<basename>.nc4`.
    Deletes any pre-existing file at the same location.

    Parameters
    ----------
    targetdir : str
        Full path to a directory, called a `targetdir` in projection system parlance.
    basename : str
        Output filename, which can exclude the extension, called a `basename` in projection system parlance.
    """
    if basename[-4:] != '.nc4':
        basename += '.nc4'
    
    # Delete any pre-existing file
    if os.path.exists(os.path.join(targetdir, basename)):
        os.remove(os.path.join(targetdir, basename))
    
    return Dataset(os.path.join(targetdir, basename), 'w', format='NETCDF4')

def create_derivative(targetdir, reader, dstname, description_suffix, extra_dependencies, limityears=None):
    """Create a NetCDF4 file which will contain data derived from aanother NetCDF4 file.
    This is used, for example, in making levels and aggregate files.

    Parameters
    ----------
    targetdir : str
        Full path to a directory, called a `targetdir` in projection system parlance.
    reader : netCDF4.Dataset
        The source file.
    dstname : str
        The basename for the derived file.
    description_suffix : str
        Added to the source description, to explain the derivation process.
    extra_dependencies : sequence of str
        Additional dependencies, to add to the list from the source file.
    limityears : function(sequence of int) (optional)
        If provided, called to return the years that will be included in the final file.

    Returns
    -------
    tuple of the NetCDF4 writer object (netCDF4.Dataset), regions variable (netCDF4.Variable),
    and years variable (netCDF4.Variable).
    """

    ## Create the new file
    writer = create(targetdir, dstname)

    ## Add additional information in order of importance, allowing failures
    try:
        writer.description = reader.description + description_suffix
        writer.version = reader.version
        if extra_dependencies:
            writer.dependencies = reader.version + ', ' + ', '.join(extra_dependencies)
        else:
            writer.dependencies = reader.version
            
        writer.author = reader.author
    except Exception as ex:
        print("WARNING: Not all descriptive attributes are included in the source file.")
        print(str(ex))
        pass

    # Construct the years variable
    years = make_years_variable(writer)
    years[:] = get_years(reader, limityears)

    # Construct the regions variable
    regions = reader.variables['regions'][:].tolist()
    make_regions_variable(writer, regions, 'regions')

    return writer, regions, years

def make_years_variable(rootgrp):
    """Create a 'year' dimension and an associated, uninitialized `years` variable.

    Parameters
    ----------
    rootgrp : netCDF4.Dataset
        The object being created.

    Returns
    -------
    years variable (netCDF4.Variable)
    """

    # Create the dimension, with unlimited length
    year = rootgrp.createDimension('year', None)

    # Create the years variable
    years = rootgrp.createVariable('year','i4',('year',))
    years.long_title = "Impact year (Gregorian calendar)"
    years.units = "Years"
    years.source = "From the weather file."

    return years

def make_months_variable(rootgrp, long_title):
    """Create a 'month' dimension and an associated, uninitialized `months` variable.

    Parameters
    ----------
    rootgrp : netCDF4.Dataset
        The object being created.

    Returns
    -------
    months variable (netCDF4.Variable)
    """

    # Create the dimension, with unlimited length
    month = rootgrp.createDimension('month', None)

    # Create the months variable
    months = rootgrp.createVariable('month','i4',('month',))
    months.long_title = long_title
    months.units = "Months"
    months.source = "From the weather file."

    return months

def make_regions_variable(rootgrp, regstrs, subset):
    """Create a 'region' dimension and an associated `regions` variable.

    Parameters
    ----------
    rootgrp : netCDF4.Dataset
        The object being created.
    regstrs : sequence of str
        The full list of region naames.
    subset : str or None
        If not none, appended to the long_title to explain any subsetting

    Returns
    -------
    regionss variable (netCDF4.Variable)
    """

    # Create the dimension, with length equal to regstrs
    region = rootgrp.createDimension('region', len(regstrs))

    # Create the regions variable
    regions = rootgrp.createVariable('regions', str, ('region',))
    regions.long_title = "Region ID" + (", " + subset if subset is not None else "")
    regions.units = "None"
    regions.source = "From the hierarchy file."

    # Initialize it with the given values
    for ii in range(len(regstrs)):
        regions[ii] = regstrs[ii]

    return regions

def make_str_variable(rootgrp, dimname, name, texts, long_title):
    strdim = rootgrp.createDimension(dimname, len(texts))

    strvar = rootgrp.createVariable(name, str, (dimname,))
    strvar.long_title = long_title
    strvar.units = "None"

    for ii in range(len(texts)):
        strvar[ii] = texts[ii]

    return strvar    

binlimits = [-np.inf, -13, -8, -3, 2, 7, 12, 17, 22, 27, 32, np.inf]
tbinslen = len(binlimits) - 2
dropbin = 8

def make_bins_variables(rootgrp):
    tbin = rootgrp.createDimension('tbin', len(binlimits) - 2)

    binlos = rootgrp.createVariable('binlos','i4',('tbin',))
    binlos[:] = [-100] + binlimits[1:dropbin] + binlimits[dropbin+1:-1]

    binhis = rootgrp.createVariable('binhis','i4',('tbin',))
    binhis[:] = binlimits[1:dropbin] + binlimits[dropbin+1:-1] + [100]

def make_betas_variables(rootgrp, num):
    betadim = rootgrp.createDimension('betadim', num)

def get_years(reader, limityears=None):
    """Return the vector of years in reader.

    Extracts either a `year` or `years` variable from the given Dataset.

    Parameters
    ----------
    reader : netCDF4.Dataset
        Dataset with a `year` or `years` variable.
    limityears : function(sequence), option
        Filters the years extracted before returning.

    Returns
    -------
    sequence of int
        Years from the reader object.
    """
    # Look for the years variable
    if 'year' in reader.variables:
        readeryears = reader.variables['year'][:]
    elif 'years' in reader.variables:
        readeryears = reader.variables['years'][:]
    else:
        raise RuntimeError("Cannot find years variable")

    # Limit the results if offered
    if limityears is not None:
        readeryears = limityears(readeryears)

    if len(readeryears) == 0:
        raise ValueError("Incomplete!")

    return readeryears
