import numpy as np

def make_years_variable(rootgrp):
    year = rootgrp.createDimension('year', None)

    years = rootgrp.createVariable('year','i4',('year',))
    years.long_title = "Impact year (Gregorian calendar)"
    years.units = "Years"
    years.source = "From the weather file."

    return years

def make_months_variable(rootgrp, long_title):
    month = rootgrp.createDimension('month', None)

    months = rootgrp.createVariable('month','i4',('month',))
    months.long_title = long_title
    months.units = "Months"
    months.source = "From the weather file."

    return months

def make_regions_variable(rootgrp, regstrs, subset):
    region = rootgrp.createDimension('region', len(regstrs))

    regions = rootgrp.createVariable('regions', str, ('region',))
    regions.long_title = "Region ID" + (", " + subset if subset is not None else "")
    regions.units = "None"
    regions.source = "From the hierarchy file."

    for ii in range(len(regstrs)):
        regions[ii] = regstrs[ii]

    return regions

binlimits = [-np.inf, -13, -8, -3, 2, 7, 12, 17, 22, 27, 32, np.inf]
tbinslen = len(binlimits) - 2
dropbin = 8

def make_bins_variables(rootgrp):
    tbin = rootgrp.createDimension('tbin', len(binlimits) - 2)

    binlos = rootgrp.createVariable('binlos','i4',('tbin',))
    binlos[:] = [-100] + binlimits[1:dropbin] + binlimits[dropbin+1:-1]

    binhis = rootgrp.createVariable('binhis','i4',('tbin',))
    binhis[:] = binlimits[1:dropbin] + binlimits[dropbin+1:-1] + [100]
