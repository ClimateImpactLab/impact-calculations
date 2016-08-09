from netCDF4 import Dataset
import helpers.header as headre
import impacts.nc4writer

def simultaneous_application(weatherbundle, calculation, get_apply_args, regions=None):
    if regions is None:
        regions = weatherbundle.regions

    print "Creating calculations..."
    applications = []
    for region in regions:
        applyargs = get_apply_args(region) if get_apply_args else []
        applications.append(calculation.apply(region, *applyargs))

    print "Processing years..."
    for yyyyddd, values in weatherbundle.yearbundles():
        if values.shape[-1] < len(applications):
            print "WARNING: fewer regions in weather than expected; dropping from end."
            applications = applications[:values.shape[-1]]

        print "Push", int(yyyyddd[0] / 1000)

        for ii in range(len(applications)):
            jj = ii if regions == weatherbundle.regions else weatherbundle.regions.index(regions[ii])

            if len(values.shape) == 3:
                if values.shape[0] == 12:
                    for yearresult in applications[ii].push(yyyyddd, values[:, :, jj]):
                        yield (ii, yearresult[0], yearresult[1:])
                else:
                    raise RuntimeError("Unknown format for weather")
            else:
                for yearresult in applications[ii].push(yyyyddd, values[:, jj]):
                    yield (ii, yearresult[0], yearresult[1:])

    for ii in range(len(applications)):
        for yearresult in applications[ii].done():
            yield (ii, yearresult[0], yearresult[1:])

    calculation.cleanup()

def write_ncdf(targetdir, camelcase, weatherbundle, calculation, get_apply_args, description, calculation_dependencies, suffix=''):
    my_regions = weatherbundle.regions

    rootgrp = Dataset(os.path.join(targetdir, undercase(camelcase) + suffix + '.nc4'), 'w', format='NETCDF4')
    rootgrp.description = description
    rootgrp.version = headre.dated_version(camelcase)
    rootgrp.dependencies = ', '.join([weatherbundle.version] + weatherbundle.dependencies + calculation_dependencies)
    rootgrp.author = "James Rising"

    years = nc4writer.make_years_variable(rootgrp)
    regions = nc4writer.make_regions_variable(rootgrp, my_regions, None)

    yeardata = weatherbundle.get_years()

    infos = calculation.column_info()
    columns = []
    # Store all in columndata, for faster feeding in
    columndata = [] # [matrix(year x region)]
    for ii in range(len(calculation.unitses)):
        column = rootgrp.createVariable(infos[ii]['name'], 'f8', ('year', 'region'))
        column.long_title = infos[ii]['title']
        column.units = calculation.unitses[ii]
        column.source = infos[ii]['description']

        columns.append(column)
        columndata.append(np.zeros((len(yeardata), len(my_regions))))

    years[:] = yeardata

    for ii, year, results in simultaneous_application(weatherbundle, calculation, get_apply_args, regions=my_regions):
        for col in range(len(results)):
            columndata[col][year - yeardata[0], ii] = results[col]

    for col in range(len(results)):
        columns[col][:, :] = columndata[col]

    rootgrp.close()

