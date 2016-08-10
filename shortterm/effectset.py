import os
import numpy as np
from netCDF4 import Dataset
import helpers.header as headre
from impacts import effectset, nc4writer

def simultaneous_application(qval, weatherbundle, calculation, get_apply_args, regions=None):
    if regions is None:
        regions = weatherbundle.regions

    print "Creating calculations..."
    applications = []
    for region in regions:
        applyargs = get_apply_args(region) if get_apply_args else []
        applications.append(calculation.apply(region, *applyargs))

    print "Processing months..."
    for month, values in weatherbundle.monthbundles(qval):
        if values.shape[-1] < len(applications):
            print "WARNING: fewer regions in weather than expected; dropping from end."
            applications = applications[:values.shape[-1]]

        print "Push", month

        for ii in range(len(applications)):
            jj = ii if regions == weatherbundle.regions else weatherbundle.regions.index(regions[ii])

            for monthresult in applications[ii].push([month], [values[jj]]):
                yield (ii, monthresult[0], monthresult[1:])

    for ii in range(len(applications)):
        for monthresult in applications[ii].done():
            yield (ii, monthresult[0], monthresult[1:])

    calculation.cleanup()

def write_ncdf(qval, targetdir, camelcase, weatherbundle, calculation, get_apply_args, description, calculation_dependencies, suffix=''):
    my_regions = weatherbundle.regions

    rootgrp = Dataset(os.path.join(targetdir, effectset.undercase(camelcase) + suffix + '.nc4'), 'w', format='NETCDF4')
    rootgrp.description = description
    rootgrp.version = headre.dated_version(camelcase)
    rootgrp.dependencies = ', '.join([weatherbundle.version] + weatherbundle.dependencies + calculation_dependencies)
    rootgrp.author = "James Rising"

    monthdata, months_title = weatherbundle.get_months()

    months = nc4writer.make_months_variable(rootgrp, months_title)
    regions = nc4writer.make_regions_variable(rootgrp, my_regions, None)

    infos = calculation.column_info()
    columns = []
    # Store all in columndata, for faster feeding in
    columndata = [] # [matrix(month x region)]
    for ii in range(len(calculation.unitses)):
        column = rootgrp.createVariable(infos[ii]['name'], 'f8', ('month', 'region'))
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

