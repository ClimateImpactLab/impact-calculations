import os, glob
from impactlab_tools.utils import files
from generate import weather, server, effectset, caller, checks
from climate.discover import discover_variable, discover_derived_variable

def preload():
    pass

def get_bundle_iterator():
    return weather.iterate_bundles(discover_variable(files.sharedpath('climate/BCSD/aggregation/cmip5/IR_level'), 'tasmax'),
                                   discover_derived_variable(files.sharedpath('climate/BCSD/aggregation/cmip5/IR_level'), 'tasmax', 'power2'),
                                   discover_derived_variable(files.sharedpath('climate/BCSD/aggregation/cmip5/IR_level'), 'tasmax', 'power3'),
                                   discover_derived_variable(files.sharedpath('climate/BCSD/aggregation/cmip5/IR_level'), 'tasmax', 'power4'))

def check_doit(targetdir, basename, suffix, deletebad=False):
    filepath = os.path.join(targetdir, basename + suffix + '.nc4')
    if not os.path.exists(filepath):
        print "REDO: Cannot find", filepath
        return True

    # Check if has 100 valid years
    if not checks.check_result_100years(filepath):
        print "REDO: Incomplete", basename, suffix
        if deletebad:
            os.remove(filepath)
        return True

    return False

def produce(targetdir, weatherbundle, economicmodel, pvals, config, result_callback=None, push_callback=None, suffix='', profile=False, diagnosefile=False):
    if config['do_only'] is None or config['do_only'] == 'acp':
        pass

    if config['do_only'] is None or config['do_only'] == 'interpolation':
        if result_callback is None:
            result_callback = lambda reg, yr, res, calc, mod: None
        if push_callback is None:
            push_callback = lambda reg, yr, app, predget, mod: None

        for filepath in glob.glob(files.sharedpath("social/parameters/labor/*.csvv")):
            basename = os.path.basename(filepath)[:-5]

            # Full Adaptation
            if check_doit(targetdir, basename, suffix):
                print "Smart Farmer"
                calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(filepath, 'impacts.labor.global20170216', weatherbundle, economicmodel, pvals[basename])

                effectset.generate(targetdir, basename + suffix, weatherbundle, calculation, "Extensive margin labor impacts, with interpolation and adaptation through interpolation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, result_callback=lambda reg, yr, res, calc: result_callback(reg, yr, res, calc, basename), push_callback=lambda reg, yr, app: push_callback(reg, int(yr) / 1000, app, baseline_get_predictors, basename), do_interpbins=False, diagnosefile=diagnosefile.replace('.csv', '-' + basename + '.csv') if diagnosefile else False)

            if config['do_farmers'] and not weatherbundle.is_historical():
                # Lock in the values
                pvals[basename].lock()

                # Comatose Farmer
                if check_doit(targetdir, basename + "-comatose", suffix):
                    print "Comatose Farmer"
                    calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(filepath, 'impacts.labor.global20170216', weatherbundle, economicmodel, pvals[basename], farmer='coma')
                    effectset.generate(targetdir, basename + "-comatose" + suffix, weatherbundle, calculation, "Extensive margin labor impacts, with no adaptation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, result_callback=lambda reg, yr, res, calc: result_callback(reg, yr, res, calc, basename + '-coma'), push_callback=lambda reg, yr, app: push_callback(reg, int(yr) / 1000, app, baseline_get_predictors, basename), do_interpbins=False)

                # Dumb Farmer
                if check_doit(targetdir, basename + "-dumb", suffix):
                    print "Dumb Farmer"
                    calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(filepath, 'impacts.labor.global20170216', weatherbundle, economicmodel, pvals[basename], farmer='dumb')
                    effectset.generate(targetdir, basename + "-dumb" + suffix, weatherbundle, calculation, "Extensive margin labor impacts, with interpolation and only environmental adaptation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, result_callback=lambda reg, yr, res, calc: result_callback(reg, yr, res, calc, basename + '-dumb'), push_callback=lambda reg, yr, app: push_callback(reg, int(yr) / 1000, app, baseline_get_predictors, basename), do_interpbins=False)
