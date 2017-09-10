import os
import numpy as np
from netCDF4 import Dataset
import helpers.header as headre
from generate import nc4writer

def simultaneous_application(qval, weatherbundle, calculation, get_apply_args, regions=None, region_callback=None):
    if regions is None:
        regions = weatherbundle.regions

    print "Creating calculations..."
    applications = []
    for region in regions:
        applyargs = get_apply_args(region) if get_apply_args else []
        applications.append(calculation.apply(region, *applyargs))

    print "Processing months..."
    for ds in weatherbundle.monthbundles(qval):
        if ds.regions.shape[0] < len(applications):
            print "WARNING: fewer regions in weather than expected (%d < %d); dropping from end." % (ds.regions.shape[0], len(applications))
            applications = applications[:ds.regions.shape[0]]

        print "Push", ds.time.values[0]

        for ii in range(len(applications)):
            for monthresult in applications[ii].push(ds.sel(region=regions[ii])):
                yield (ii, monthresult[0], monthresult[1:])

    for ii in range(len(applications)):
        for monthresult in applications[ii].done():
            yield (ii, monthresult[0], monthresult[1:])

    calculation.cleanup()

def write_ncdf(qval, targetdir, title, weatherbundle, calculation, get_apply_args, description, calculation_dependencies):
    my_regions = weatherbundle.regions

    rootgrp = Dataset(os.path.join(targetdir, title + '.nc4'), 'w', format='NETCDF4')
    rootgrp.description = description
    rootgrp.version = headre.dated_version(title)
    rootgrp.dependencies = ', '.join([weatherbundle.version] + weatherbundle.dependencies + calculation_dependencies)
    rootgrp.author = "James Rising"

    monthdata, months_title = weatherbundle.get_months()

    months = nc4writer.make_months_variable(rootgrp, months_title)
    regions = nc4writer.make_regions_variable(rootgrp, my_regions, None)

    infos = calculation.column_info()
    columns = []
    # Store all in columndata, for faster feeding in
    columndata = [] # [matrix(month x region)]
    usednames = set()
    for ii in range(len(calculation.unitses)):
        myname = infos[ii]['name']
        while myname in usednames:
            myname += "2"
        usednames.add(myname)

        column = rootgrp.createVariable(myname, 'f8', ('month', 'region'))
        column.long_title = infos[ii]['title']
        column.units = calculation.unitses[ii]
        column.source = infos[ii]['description']

        columns.append(column)
        columndata.append(np.zeros((len(monthdata), len(my_regions))))

    months[:] = monthdata

    for ii, month, results in simultaneous_application(qval, weatherbundle, calculation, get_apply_args, regions=my_regions):
        for col in range(len(results)):
            columndata[col][month - monthdata[0], ii] = results[col]

    for col in range(len(results)):
        columns[col][:, :] = columndata[col]

    rootgrp.close()

    byname = {}
    for col in range(len(results)):
        myname = infos[col]['name']
        while myname in byname:
            myname += "2"
        byname[myname] = columndata[col]

    return byname
