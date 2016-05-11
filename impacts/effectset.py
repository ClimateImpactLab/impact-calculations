import re, yaml, os, time
import numpy as np
from netCDF4 import Dataset
import helpers.header as headre
from openest.generate import retrieve
from adaptation import adapting_curve
import server, nc4writer

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

        print "Push", int(yyyyddd[0] / 1000)

        for ii in range(len(applications)):
            jj = ii if regions == weatherbundle.regions else weatherbundle.regions.index(regions[ii])
            for yearresult in applications[ii].push(yyyyddd, values[:, jj]):
                yield (ii, yearresult[0], yearresult[1:])
            if push_callback is not None:
                push_callback(regions[ii], int(yyyyddd[0] / 1000), applications[ii])

    for ii in range(len(applications)):
        for yearresult in applications[ii].done():
            yield (ii, yearresult[0], yearresult[1:])

    calculation.cleanup()

def write_ncdf(targetdir, camelcase, weatherbundle, calculation, get_apply_args, description, calculation_dependencies, filter_region=None, result_callback=None, push_callback=None, subset=None, do_interpbins=False, suffix=''):
    if filter_region is None:
        my_regions = weatherbundle.regions
    else:
        my_regions = []
        for ii in range(len(weatherbundle.regions)):
            if filter_region(weatherbundle.regions[ii]):
                my_regions.append(weatherbundle.regions[ii])

    rootgrp = Dataset(os.path.join(targetdir, undercase(camelcase) + suffix + '.nc4'), 'w', format='NETCDF4')
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
    for ii in range(len(calculation.unitses)):
        column = rootgrp.createVariable(infos[ii]['name'], 'f8', ('year', 'region'))
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

    for ii, year, results in simultaneous_application(weatherbundle, calculation, get_apply_args, regions=my_regions, push_callback=push_callback):
        if result_callback is not None:
            result_callback(my_regions[ii], year, results, calculation)
        for col in range(len(results)):
            columndata[col][year - yeardata[0], ii] = results[col]
        if do_interpbins:
            curve = adapting_curve.region_stepcurves[my_regions[ii]].curr_curve
            betasdata[:, year - yeardata[0], ii] = list(curve.yy[:nc4writer.dropbin]) + list(curve.yy[nc4writer.dropbin+1:])

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

class ConstantPvals:
    def __init__(self, value):
        self.value = value

    def lock(self):
        pass

    def __getitem__(self, name):
        return ConstantDictionary(self.value)

    def __iter__(self):
        yield ('all', self.value)

class ConstantDictionary:
    def __init__(self, value):
        self.value = value

    def lock(self):
        pass

    def __getitem__(self, name):
        return self.value

    def get_seed(self):
        return None # for MC, have this also increment state

class OnDemandRandomPvals:
    def __init__(self):
        self.dicts = {}
        self.locked = False

    def lock(self):
        self.locked = True
        for key in self.dicts:
            self.dicts[key].lock()

    def __getitem__(self, name):
        mydict = self.dicts.get(name, None)
        if mydict is None and not self.locked:
            mydict = OnDemandRandomDictionary()
            self.dicts[name] = mydict

        return mydict

    def __iter__(self):
        for key in self.dicts:
            yield (key, self.dicts[key].values)

class OnDemandRandomDictionary:
    def __init__(self):
        self.values = {}
        self.locked = False

    def lock(self):
        self.locked = True

    def __getitem__(self, name):
        value = self.values.get(name, np.nan)
        if np.isnan(value) and not self.locked:
            value = np.random.uniform()
            self.values[name] = value

        return value

    def get_seed(self):
        if self.locked:
            return self.values['seed'][0]

        seed = int(time.time())
        if 'seed' in self.values:
            self.values['seed'].append(seed)
        else:
            self.values['seed'] = [seed]

        return seed

def get_model_server(id):
    result = re.search(r"collection_id=([a-z0-9]+)", id)
    if result:
        return retrieve.ddp_from_url(server.full_url(id))

    return retrieve.any_from_url(server.full_url('/model/download?id=' + id + '&permission_override=true'))

def make_pval_file(targetdir, pvals):
    with open(os.path.join(targetdir, "pvals.yml"), 'w') as fp:
        fp.write(yaml.dump(dict(pvals)))
