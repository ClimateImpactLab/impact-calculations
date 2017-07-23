import re, yaml, os, time
import numpy as np
from netCDF4 import Dataset
import helpers.header as headre
from openest.generate import retrieve, diagnostic
from adaptation import curvegen
import server, nc4writer

def simultaneous_application(weatherbundle, calculation, get_apply_args, regions=None, push_callback=None):
    if regions is None:
        regions = weatherbundle.regions

    print "Creating calculations..."
    applications = []
    for region in regions:
        applyargs = get_apply_args(region) if get_apply_args else []
        applications.append(calculation.apply(region, *applyargs))

    print "Processing years..."
    for weatherslice in weatherbundle.yearbundles():
        if weatherslice.weathers.shape[1] < len(applications):
            print "WARNING: fewer regions in weather than expected; dropping from end."
            applications = applications[:weatherslice.weathers.shape[1]]

        print "Push", weatherslice.get_years()[0]

        for ii in range(len(applications)):
            jj = ii if regions == weatherbundle.regions else weatherbundle.regions.index(regions[ii])

            for yearresult in applications[ii].push(weatherslice.select_region(jj)):
                yield (ii, yearresult[0], yearresult[1:])

            if push_callback is not None:
                push_callback(regions[ii], weatherslice.get_years()[0], applications[ii])

    for ii in range(len(applications)):
        for yearresult in applications[ii].done():
            yield (ii, yearresult[0], yearresult[1:])

    calculation.cleanup()

def get_ncdf_path(targetdir, basename, suffix=''):
    return os.path.join(targetdir, basename + suffix + '.nc4')

def generate(targetdir, basename, weatherbundle, calculation, get_apply_args, description, calculation_dependencies, config, filter_region=None, result_callback=None, push_callback=None, subset=None, suffix='', diagnosefile=False):
    if config['mode'] == 'profile':
        return small_print(weatherbundle, calculation, get_apply_args, regions=10)

    if config['mode'] == 'diagnostic':
        return small_print(weatherbundle, calculation, get_apply_args, regions=[config['region']])

    if filter_region is None:
        filter_region = config.get('filter_region', None)
    
    return write_ncdf(targetdir, basename, weatherbundle, calculation, get_apply_args, description, calculation_dependencies, filter_region=filter_region, result_callback=result_callback, push_callback=push_callback, subset=subset, suffix=suffix, diagnosefile=diagnosefile)

def write_ncdf(targetdir, basename, weatherbundle, calculation, get_apply_args, description, calculation_dependencies, filter_region=None, result_callback=None, push_callback=None, subset=None, suffix='', diagnosefile=False):
    if filter_region is None:
        my_regions = weatherbundle.regions
    else:
        my_regions = []
        for ii in range(len(weatherbundle.regions)):
            if isinstance(filter_region, str):
                if weatherbundle.regions[ii] in filter_region:
                    my_regions.append(weatherbundle.regions[ii])
            else:
                if filter_region(weatherbundle.regions[ii]):
                    my_regions.append(weatherbundle.regions[ii])

    rootgrp = Dataset(get_ncdf_path(targetdir, basename, suffix), 'w', format='NETCDF4')
    rootgrp.description = description
    rootgrp.version = headre.dated_version(basename)
    rootgrp.dependencies = ', '.join([weatherbundle.version] + weatherbundle.dependencies + calculation_dependencies)
    rootgrp.author = "James Rising"

    years = nc4writer.make_years_variable(rootgrp)
    regions = nc4writer.make_regions_variable(rootgrp, my_regions, subset)

    yeardata = weatherbundle.get_years()

    infos = calculation.column_info()
    print calculation.unitses
    columns = []
    # Store all in columndata, for faster feeding in
    columndata = [] # [matrix(year x region)]
    usednames = [] # In order of infos
    for ii in range(len(calculation.unitses)):
        myname = infos[ii]['name']
        while myname in usednames:
            myname += "2"
        usednames.append(myname)

        column = rootgrp.createVariable(myname, 'f8', ('year', 'region'))
        column.long_title = infos[ii]['title']
        column.units = calculation.unitses[ii]
        column.source = infos[ii]['description']

        columns.append(column)
        columndata.append(np.zeros((len(yeardata), len(my_regions))))

    nc4writer.make_str_variable(rootgrp, 'operation', 'orderofoperations', list(reversed(usednames)),
                                "Order of the operations applied to the input weather data.")

    years[:] = yeardata

    if diagnosefile:
        diagnostic.begin(diagnosefile)

    for ii, year, results in simultaneous_application(weatherbundle, calculation, get_apply_args, regions=my_regions, push_callback=push_callback):
        if result_callback is not None:
            result_callback(my_regions[ii], year, results, calculation)
        for col in range(len(results)):
            columndata[col][year - yeardata[0], ii] = results[col]
        if diagnosefile:
            diagnostic.finish(my_regions[ii], year)

    if diagnosefile:
        diagnostic.close()

    for col in range(len(results)):
        columns[col][:, :] = columndata[col]

    rootgrp.close()

def small_print(weatherbundle, calculation, get_apply_args, regions=10):
    """
    Generate results for a small set of regions, and print out the results without generating any files.

    Args:
        regions: May be a number (e.g., 10) or a list of region codes
    """
    if isinstance(regions, int):
        regions = np.random.choice(weatherbundle.regions, regions).tolist()

    yeardata = weatherbundle.get_years()
    values = [np.zeros((len(yeardata), len(regions))) for ii in range(len(calculation.unitses))]
    for ii, year, results in simultaneous_application(weatherbundle, calculation, get_apply_args, regions=regions):
        for col in range(len(results)):
            values[col][year - yeardata[0]] = results[col]
        if year > 2020:
            break
        
    return values

def get_model_server(id):
    result = re.search(r"collection_id=([a-z0-9]+)", id)
    if result:
        return retrieve.ddp_from_url(server.full_url(id))

    return retrieve.any_from_url(server.full_url('/model/download?id=' + id + '&permission_override=true'))
