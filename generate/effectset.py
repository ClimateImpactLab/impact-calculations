import re, yaml, os, time
import numpy as np
import xarray as xr
from netCDF4 import Dataset
import helpers.header as headre
from openest.generate import retrieve, diagnostic, fast_dataset
from adaptation import curvegen
from . import server, nc4writer


def simultaneous_application(weatherbundle, calculation, regions=None, push_callback=None):
    """Iterate weather, calculations, generating regional results per time step

    Parameters
    ----------
    weatherbundle : generate.weather.DailyWeatherBundle
        Its ``regions`` may be parsed and ``yearbundle`` is iterated.
    calculation : openest.generate.functions.SpanInstabase
        Its ``apply`` method is passed items from ``regions``, if given.
        Afterwards, its ``cleanup`` method is called.
    regions : Iterable of str or None, optional:
        One or more regions to perform calculations for. If None, uses all
        regions available in ``weatherbundle.regions``.
    push_callback : Callable or None, optional
        Used for diagnostic purposes. Must accept three arguments. A year, a
        str region, and whatever is returned from ``calculation.apply()`` when
        passed region.

    Yields
    -------
    region : str
    result_year : int
        First element of Sequential returned by `calculation` after `apply` has
        been given a region, and pushed data output from weatherbundle for a
        given year, in a given region.
    result : list
        Remaining elements returned from `calculation`, as described above,
        without `result_year`.
    """
    if regions is None:
        regions = weatherbundle.regions

    print("Creating calculations...")
    applications = {}
    for region in regions:
        applications[region] = calculation.apply(region)

    region_indices = {region: weatherbundle.regions.index(region) for region in regions}

    print("Processing years...")
    for year, ds in weatherbundle.yearbundles():
        if ds.region.shape[0] < len(applications):
            print("WARNING: fewer regions in weather than expected; dropping from end.")

        print("Push", year)
        for region, subds in fast_dataset.region_groupby(ds, year, regions, region_indices):
            for yearresult in applications[region].push(subds):
                yield (region, yearresult[0], yearresult[1:])

            if push_callback is not None:
                push_callback(region, year, applications[region])
                diagnostic.finish(region, year, group='input')

    for region in applications:
        for yearresult in applications[region].done():
            yield (region, yearresult[0], yearresult[1:])

    calculation.cleanup()

def generate(targetdir, basename, weatherbundle, calculation, description, calculation_dependencies, config, filter_region=None, push_callback=None, subset=None, diagnosefile=False, deltamethod_vcv=False):
    if 'mode' in config and config['mode'] == 'profile':
        return small_print(weatherbundle, calculation, regions=10000)

    if 'mode' in config and config['mode'] == 'diagnostic':
        return small_print(weatherbundle, calculation, regions=[config['region']])

    if filter_region is None:
        filter_region = config.get('filter-region', None)

    if deltamethod_vcv is not False:
        calculation.enable_deltamethod()

    return write_ncdf(targetdir, basename, weatherbundle, calculation, description, calculation_dependencies, filter_region=filter_region, push_callback=push_callback, subset=subset, diagnosefile=diagnosefile, deltamethod_vcv=deltamethod_vcv)

def write_ncdf(targetdir, basename, weatherbundle, calculation, description, calculation_dependencies, filter_region=None, push_callback=None, subset=None, diagnosefile=False, deltamethod_vcv=False):
    """Compute and write impact projection to NetCDF file

    No values are returned. This function writes projected values to a NetCDF
    file. It may also write a diagnostic file, if specified.

    Parameters
    ----------
    targetdir : str
        Directory to write files to.
    basename : str
        Projection basename. Used for file naming.
    weatherbundle : generate.weather.DailyWeatherBundle
        Populated weather data to compute projection over.
    calculation : openest.generate.functions.SpanInstabase
        Projection calculations to apply to `weatherbundle`.
    description : str
        Description of projection for output file metadata.
    calculation_dependencies : Iterable of str
    filter_region : str or None, optional
        One or more regions to perform calculations for. If None, uses all
        regions available in ``weatherbundle.regions``.
    push_callback : Callable or None, optional
        Passed to ``generate.effectset.simultaneous_application``.
    subset : str or None, optional
        Regional subsetting used to make region variable in output NetCDF file.
        Passed to ``nc4writer.make_regions_variable``.
    diagnosefile : str or bool, optional
        Path to file for writing projection run diagnostic CSV file. If
        ``False``, no diagnostics are output.
    deltamethod_vcv : ndarray or bool, optional
        2D variance-covariance float array if the projection is to run with the
        delta method. If ``False``, the delta method is not used.
    """
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
        print("Failed to open file for writing at " + os.path.join(targetdir, basename + '.nc4'))
        raise ex

    rootgrp.description = description
    rootgrp.version = headre.dated_version(basename)
    rootgrp.dependencies = ', '.join([weatherbundle.version] + weatherbundle.dependencies + calculation_dependencies)
    rootgrp.author = "James Rising"

    years = nc4writer.make_years_variable(rootgrp)
    regions = nc4writer.make_regions_variable(rootgrp, my_regions, subset)

    if deltamethod_vcv is not False:
        rootgrp.createDimension('coefficient', deltamethod_vcv.shape[0])

        vcv = rootgrp.createVariable('vcv', 'f4', ('coefficient', 'coefficient'))
        vcv.long_title = "Variance covariance matrix"
        vcv[:, :] = deltamethod_vcv

    yeardata = weatherbundle.get_years()

    infos = calculation.column_info()
    columns = []
    # Store all in columndata, for faster feeding in
    columndata = [] # [matrix(year x region)]
    usednames = [] # In order of infos
    for ii in range(len(calculation.unitses)):
        myname = infos[ii]['name']
        while myname in usednames:
            myname += "2"
        usednames.append(myname)

        column = rootgrp.createVariable(myname, 'f4', ('year', 'region'))
        column.long_title = infos[ii]['title']
        column.units = calculation.unitses[ii]
        column.source = infos[ii]['description']

        columns.append(column)
        columndata.append(np.zeros((len(yeardata), len(my_regions))) * np.nan)

        if deltamethod_vcv is not False:
            column = rootgrp.createVariable(myname + '_bcde', 'f4', ('coefficient', 'year', 'region'))
            column.long_title = infos[ii]['title'] + " by coefficient deltamethod evaluation"

            columns.append(column)
            columndata.append(np.zeros((deltamethod_vcv.shape[0], len(yeardata), len(my_regions))) * np.nan)

    nc4writer.make_str_variable(rootgrp, 'operation', 'orderofoperations', list(reversed(usednames)),
                                "Order of the operations applied to the input weather data.")

    years[:] = yeardata

    if diagnosefile:
        diagnostic.begin(diagnosefile, finishset=set(['input', 'output']))

    region_indices = {region: my_regions.index(region) for region in my_regions}

    for region, year, results in simultaneous_application(weatherbundle, calculation, regions=my_regions, push_callback=push_callback):
        for col in range(len(results)):
            if deltamethod_vcv is not False:
                variance = 0
                for ii in range(len(results[col])):
                    for jj in range(len(results[col])):
                        variance += deltamethod_vcv[ii, jj] * results[col][ii] * results[col][jj]
                columndata[2 * col][year - yeardata[0], region_indices[region]] = variance
                columndata[2 * col + 1][:, year - yeardata[0], region_indices[region]] = results[col]
            else:
                columndata[col][year - yeardata[0], region_indices[region]] = results[col]
        if diagnosefile:
            diagnostic.finish(region, year, group='output')

    if diagnosefile:
        diagnostic.close()

    for col in range(len(results)):
        if deltamethod_vcv is not False:
            columns[2 * col][:, :] = columndata[2 * col]
            columns[2 * col + 1][:, :, :] = columndata[2 * col + 1]
        else:
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
