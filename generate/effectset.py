import re, yaml, os, time
import numpy as np
from netCDF4 import Dataset
import helpers.header as headre
from openest.generate import retrieve, diagnostic
from adaptation import adapting_curve
import server, nc4writer
from pvalses import *

def undercase(camelcase):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camelcase)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def simultaneous_application(weatherbundle, calculation, get_apply_args, regions=None, push_callback=None):
    if regions is None:
        regions = weatherbundle.regions

    print "Creating calculations..."
    applications = []
    for region in regions:
        applyargs = get_apply_args(region) if get_apply_args else []
        applications.append(calculation.apply(region, *applyargs))

    print "Processing years..."
    for yyyyddd, values in weatherbundle.yearbundles():
        if values.shape[1] < len(applications):
            print "WARNING: fewer regions in weather than expected; dropping from end."
            applications = applications[:values.shape[1]]

        print "Push", yyyyddd[0]

        for ii in range(len(applications)):
            jj = ii if regions == weatherbundle.regions else weatherbundle.regions.index(regions[ii])

            if len(values.shape) == 3:
                for yearresult in applications[ii].push(yyyyddd, values[:, jj, :]):
                    yield (ii, yearresult[0], yearresult[1:])
            else:
                for yearresult in applications[ii].push(yyyyddd, values[:, jj]):
                    yield (ii, yearresult[0], yearresult[1:])

            if push_callback is not None:
                push_callback(regions[ii], yyyyddd[0], applications[ii])

    for ii in range(len(applications)):
        for yearresult in applications[ii].done():
            yield (ii, yearresult[0], yearresult[1:])

    calculation.cleanup()

def get_ncdf_path(targetdir, camelcase, suffix=''):
    return os.path.join(targetdir, undercase(camelcase) + suffix + '.nc4')

def write_ncdf(targetdir, camelcase, weatherbundle, calculation, get_apply_args, description, calculation_dependencies, filter_region=None, result_callback=None, push_callback=None, subset=None, do_interpbins=False, suffix='', diagnosefile=False):
    if filter_region is None:
        my_regions = weatherbundle.regions
    else:
        my_regions = []
        for ii in range(len(weatherbundle.regions)):
            if filter_region(weatherbundle.regions[ii]):
                my_regions.append(weatherbundle.regions[ii])

    rootgrp = Dataset(get_ncdf_path(targetdir, camelcase, suffix), 'w', format='NETCDF4')
    rootgrp.description = description
    rootgrp.version = headre.dated_version(camelcase)
    rootgrp.dependencies = ', '.join([weatherbundle.version] + weatherbundle.dependencies + calculation_dependencies)
    rootgrp.author = "James Rising"

    years = nc4writer.make_years_variable(rootgrp)
    regions = nc4writer.make_regions_variable(rootgrp, my_regions, subset)

    yeardata = weatherbundle.get_years()

    infos = calculation.column_info()
    columns = []
    # Store all in columndata, for faster feeding in
    columndata = [] # [matrix(year x region)]
    usednames = set()
    for ii in range(len(calculation.unitses)):
        myname = infos[ii]['name']
        while myname in usednames:
            myname += "2"
        usednames.add(myname)

        column = rootgrp.createVariable(myname, 'f8', ('year', 'region'))
        column.long_title = infos[ii]['title']
        column.units = calculation.unitses[ii]
        column.source = infos[ii]['description']

        columns.append(column)
        columndata.append(np.zeros((len(yeardata), len(my_regions))))

    years[:] = yeardata

    if do_interpbins:
        nc4writer.make_bins_variables(rootgrp)
        betas = rootgrp.createVariable('betas', 'f8', ('tbin', 'year', 'region'))
        betas.long_title = "Response curve coefficient values"
        betas.units = calculation.unitses[-1]

        betasdata = np.zeros((nc4writer.tbinslen, len(yeardata), len(my_regions)))

    if diagnosefile:
        diagnostic.begin(diagnosefile)

    for ii, year, results in simultaneous_application(weatherbundle, calculation, get_apply_args, regions=my_regions, push_callback=push_callback):
        if result_callback is not None:
            result_callback(my_regions[ii], year, results, calculation)
        for col in range(len(results)):
            columndata[col][year - yeardata[0], ii] = results[col]
        if do_interpbins:
            curve = adapting_curve.region_stepcurves[my_regions[ii]].curr_curve
            betasdata[:, year - yeardata[0], ii] = list(curve.yy[:nc4writer.dropbin]) + list(curve.yy[nc4writer.dropbin+1:])
        if diagnosefile:
            diagnostic.finish(my_regions[ii], year)

    if diagnosefile:
        diagnostic.close()

    for col in range(len(results)):
        columns[col][:, :] = columndata[col]

    if do_interpbins:
        betas[:, :, :] = betasdata

    rootgrp.close()

def small_test(weatherbundle, calculation, get_apply_args, num_regions=10, *xargs):
    yeardata = weatherbundle.get_years()
    values = [np.zeros((len(yeardata), num_regions)) for ii in range(len(calculation.unitses))]
    for ii, year, results in simultaneous_application(weatherbundle, calculation, get_apply_args, regions=np.random.choice(weatherbundle.regions, num_regions).tolist()):
        print ii, year, results
        for col in range(len(results)):
            values[col][year - yeardata[0]] = results[col]

    return values

def get_model_server(id):
    result = re.search(r"collection_id=([a-z0-9]+)", id)
    if result:
        return retrieve.ddp_from_url(server.full_url(id))

    return retrieve.any_from_url(server.full_url('/model/download?id=' + id + '&permission_override=true'))
