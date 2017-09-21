import re, yaml, os, time
import numpy as np
import xarray as xr
from netCDF4 import Dataset
import helpers.header as headre
from openest.generate import retrieve, diagnostic, fast_dataset
from adaptation import curvegen
import server, nc4writer

def simultaneous_application(weatherbundle, calculation, regions=None, push_callback=None):
    if regions is None:
        regions = weatherbundle.regions

    print "Creating calculations..."
    applications = {}
    for region in regions:
        applications[region] = calculation.apply(region)

    region_indices = {region: weatherbundle.regions.index(region) for region in regions}
    
    print "Processing years..."
    for year, ds in weatherbundle.yearbundles():
        if ds.region.shape[0] < len(applications):
            print "WARNING: fewer regions in weather than expected; dropping from end."

        print "Push", year

        for region, subds in fast_dataset.region_groupby(ds, year, regions, region_indices):
            for yearresult in applications[region].push(subds):
                yield (region, yearresult[0], yearresult[1:])

            if push_callback is not None:
                push_callback(region, year, applications[region])

    for region in applications:
        for yearresult in applications[region].done():
            yield (region, yearresult[0], yearresult[1:])

    calculation.cleanup()

def generate(targetdir, basename, weatherbundle, calculation, description, calculation_dependencies, config, filter_region=None, push_callback=None, subset=None, diagnosefile=False):
    if 'mode' in config and config['mode'] == 'profile':
        return small_print(weatherbundle, calculation, regions=10000)

    if 'mode' in config and config['mode'] == 'diagnostic':
        return small_print(weatherbundle, calculation, regions=[config['region']])

    if filter_region is None:
        filter_region = config.get('filter_region', None)
    
    return write_ncdf(targetdir, basename, weatherbundle, calculation, description, calculation_dependencies, filter_region=filter_region, push_callback=push_callback, subset=subset, diagnosefile=diagnosefile)

def write_ncdf(targetdir, basename, weatherbundle, calculation, description, calculation_dependencies, filter_region=None, push_callback=None, subset=None, diagnosefile=False):
    if filter_region is None:
        my_regions = weatherbundle.regions
    else:
        my_regions = []
        for ii in range(len(weatherbundle.regions)):
            if isinstance(filter_region, str):
                if filter_region in weatherbundle.regions[ii]:
                    my_regions.append(weatherbundle.regions[ii])
            else:
                if filter_region(weatherbundle.regions[ii]):
                    my_regions.append(weatherbundle.regions[ii])

    try:
        rootgrp = Dataset(os.path.join(targetdir, basename + '.nc4'), 'w', format='NETCDF4')
    except Exception as ex:
        print "Failed to open file for writing at " + os.path.join(targetdir, basename + '.nc4')
        raise ex
    
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

    region_indices = {region: my_regions.index(region) for region in my_regions}
        
    for region, year, results in simultaneous_application(weatherbundle, calculation, regions=my_regions, push_callback=push_callback):
        for col in range(len(results)):
            columndata[col][year - yeardata[0], region_indices[region]] = results[col]
        if diagnosefile:
            diagnostic.finish(region, year)

    if diagnosefile:
        diagnostic.close()

    for col in range(len(results)):
        columns[col][:, :] = columndata[col]

    rootgrp.close()

def small_print(weatherbundle, calculation, regions=10):
    """
    Generate results for a small set of regions, and print out the results without generating any files.

    Args:
        regions: May be a number (e.g., 10) or a list of region codes
    """
    if isinstance(regions, int):
        regions = np.random.choice(weatherbundle.regions, regions, replace=False).tolist()

    yeardata = weatherbundle.get_years()
    values = [np.zeros((len(yeardata), len(regions))) for ii in range(len(calculation.unitses))]

    for region, year, results in simultaneous_application(weatherbundle, calculation, regions=regions):
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
