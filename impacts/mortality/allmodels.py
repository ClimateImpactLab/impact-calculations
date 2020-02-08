import os, glob, traceback
import numpy as np
from impactlab_tools.utils import files
from adaptation import csvvfile
from generate import weather, effectset, caller, checks, agglib
from openest.generate.weatherslice import YearlyWeatherSlice
from climate.discover import discover_versioned, discover_versioned_yearly, discover_day2year, standard_variable
from datastore import agecohorts

def preload():
    from datastore import library
    library.get_data('mortality-deathrates', 'deaths/person')

def get_bundle_iterator(config):
    assert 'specification' in config
    if config['specification'] == 'polynomial':
        return weather.iterate_bundles(discover_versioned(files.sharedpath("climate/BCSD/hierid/popwt/daily/tas"), 'tas', **config),
                                       discover_versioned(files.sharedpath("climate/BCSD/hierid/popwt/daily/tas-poly-2"), 'tas-poly-2', **config),
                                       discover_versioned(files.sharedpath("climate/BCSD/hierid/popwt/daily/tas-poly-3"), 'tas-poly-3', **config),
                                       discover_versioned(files.sharedpath("climate/BCSD/hierid/popwt/daily/tas-poly-4"), 'tas-poly-4', **config), **config)
    if config['specification'] == 'bins':
        return weather.iterate_bundles(discover_day2year(standard_variable('tas', 'day', **config), lambda arr: np.mean(arr, axis=0)),
                                       discover_versioned_yearly(files.sharedpath("climate/BCSD/hierid/popwt/annual/binned_tas"), "tas_bin_day_counts", **config),
                                       **config)
    if config['specification'] == 'linear':
        assert 'terms' in config
        discovers = [discover_day2year(standard_variable('tas', 'day', **config), lambda arr: np.mean(arr, axis=0))]
        for label in config['terms']:
            assert 'variable' in config['terms'][label]
            variable = config['terms'][label]['variable']
            discovers.append(discover_versioned_yearly(files.sharedpath("climate/BCSD/hierid/popwt/annual/" + variable), variable, **config))
        
        return weather.iterate_bundles(*tuple(discovers), **config)
    if config['specification'] == 'hddcdd':
        return weather.iterate_bundles(discover_day2year(standard_variable('tas', 'day', **config), lambda arr: np.mean(arr, axis=0)),
                                       discover_versioned_yearly(files.sharedpath("climate/BCSD/hierid/popwt/annual/" + config['hddvar']), config['hddvar'], **config),
                                       discover_versioned_yearly(files.sharedpath("climate/BCSD/hierid/popwt/annual/" + config['cddvar']), config['cddvar'], **config),
                                       **config)
    raise ValueError("Unknown specification: %s" % config['specification'])

def check_doit(targetdir, basename, suffix, config):
    filepath = os.path.join(targetdir, basename + suffix + '.nc4')
    if not os.path.exists(filepath):
        print "REDO: Cannot find", filepath, suffix
        return True

    # Check if has 100 valid years
    checkargs = {}
    if 'filter-region' in config:
        checkargs['regioncount'] = 1
    if not checks.check_result_100years(filepath, **checkargs):
        print "REDO: Incomplete", basename, suffix
        return True

    return False

def produce(targetdir, weatherbundle, economicmodel, pvals, config, push_callback=None, suffix='', profile=False, diagnosefile=False):
    print config['do_only']

    if config['do_only'] is None or config['do_only'] in ['interpolation', 'mle']:
        if push_callback is None:
            push_callback = lambda reg, yr, app, predget, mod: None

        csvvfiles = glob.glob(files.sharedpath(config['csvvfile']))
        specification = config['specification']
        
        for filepath in csvvfiles:
            basename = os.path.basename(filepath)[:-5]
            print basename

            # Split into age groups and lock in q-draw
            csvv = csvvfile.read(filepath)
            csvvfile.collapse_bang(csvv, pvals[basename].get_seed('csvv'))

            if specification == 'cubicspline':
                numpreds = 5
                module = 'impacts.mortality.ols_cubic_spline'
                minpath_suffix = '-splinemins'
            elif specification == 'polynomial':
                numpreds = len(csvv['prednames']) / 9
                assert numpreds * 9 == len(csvv['prednames'])
                module = 'impacts.mortality.ols_polynomial'
                minpath_suffix = '-polymins'
            elif specification == 'mle':
                numpreds = len(csvv['prednames']) / 9
                assert numpreds * 9 == len(csvv['prednames'])
                module = 'impacts.mortality.mle_polynomial'
                minpath_suffix = '-polymins'
            elif specification == 'bins':
                numpreds = 10
                module = 'impacts.mortality.ols_binned'
                minpath_suffix = '-binmins'
            elif specification == 'linear':
                numpreds = len(config['terms'])
                module = 'impacts.mortality.ols_linear'
                minpath_suffix = None
            if minpath_suffix is not None and weatherbundle.is_historical():
                minpath_suffix += "-histclim"

            agegroups = ['young', 'older', 'oldest']
            for ageii in range(len(agegroups)):
                subcsvv = csvvfile.subset(csvv, 3 * numpreds * ageii + np.arange(3 * numpreds))
                subbasename = basename + '-' + agegroups[ageii]
                if minpath_suffix is not None:
                    caller.callinfo = dict(minpath=os.path.join(targetdir, subbasename + minpath_suffix + '.csv'))

                # Full Adaptation
                if check_doit(targetdir, subbasename, suffix, config):
                    print "Smart Farmer"
                    calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(subcsvv, module, weatherbundle, economicmodel, pvals[subbasename], config=config)

                    effectset.generate(targetdir, subbasename + suffix, weatherbundle, calculation, "Mortality impacts, with interpolation and adaptation through interpolation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, push_callback=lambda reg, yr, app: push_callback(reg, yr, app, baseline_get_predictors, subbasename), diagnosefile=diagnosefile.replace('.csv', '-' + subbasename + '.csv') if diagnosefile else False)

                    if profile:
                        return

                if config['do_farmers'] == 'always' or (config['do_farmers'] and not weatherbundle.is_historical()):
                    # Lock in the values
                    pvals[subbasename].lock()

                    # Comatose Farmer
                    if check_doit(targetdir, subbasename + "-noadapt", suffix, config):
                        calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(subcsvv, module, weatherbundle, economicmodel, pvals[subbasename], farmer='coma', config=config)

                        effectset.generate(targetdir, subbasename + "-noadapt" + suffix, weatherbundle, calculation, "Mortality impacts, with interpolation but no adaptation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, push_callback=lambda reg, yr, app: push_callback(reg, yr, app, baseline_get_predictors, subbasename + '-noadapt'))

                    # Dumb Farmer
                    if check_doit(targetdir, subbasename + "-incadapt", suffix, config):
                        calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(subcsvv, module, weatherbundle, economicmodel, pvals[subbasename], farmer='dumb', config=config)

                        effectset.generate(targetdir, subbasename + "-incadapt" + suffix, weatherbundle, calculation, "Mortality impacts, with interpolation and only environmental adaptation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, push_callback=lambda reg, yr, app: push_callback(reg, yr, app, baseline_get_predictors, subbasename + '-incadapt'))

            # Combine the ages
            try:
                for assumption in ['', '-noadapt', '-incadapt']:
                    if assumption != '':
                        if config['do_farmers'] == 'always' or not config['do_farmers'] or weatherbundle.is_historical():
                            continue
                    halfweight = agecohorts.SpaceTimeBipartiteData(1950, 2100, None)
                    basenames = [basename + '-' + agegroup + assumption + suffix for agegroup in agegroups]
                    get_stweights = [lambda year0, year1: halfweight.load(year0, year1, economicmodel.model, economicmodel.scenario, 'age0-4', shareonly=True), lambda year0, year1: halfweight.load(year0, year1, economicmodel.model, economicmodel.scenario, 'age5-64', shareonly=True), lambda year0, year1: halfweight.load(year0, year1, economicmodel.model, economicmodel.scenario, 'age65+', shareonly=True)]
                    if check_doit(targetdir, basename + '-combined' + assumption, suffix, config):
                        agglib.combine_results(targetdir, basename + '-combined' + assumption, basenames, get_stweights, "Combined mortality across age-groups for " + basename, suffix=suffix)
            except Exception as ex:
                print "TO FIX: Combining failed."
                traceback.print_exc()
