import os, glob
from impactlab_tools.utils import files
from generate import weather, server, effectset, caller, checks
from climate.discover import discover_variable, discover_derived_variable

def preload():
    pass

def get_bundle_iterator():
    return weather.iterate_bundles(discover_versioned(files.sharedpath("climate/BCSD/hierid/popwt/daily/tasmax"), 'tasmax'),
                                   discover_versioned(files.sharedpath("climate/BCSD/hierid/popwt/daily/tasmax-poly-2"), 'tasmax-poly-2'),
                                   discover_versioned(files.sharedpath("climate/BCSD/hierid/popwt/daily/tasmax-poly-3"), 'tasmax-poly-3'),
                                   discover_versioned(files.sharedpath("climate/BCSD/hierid/popwt/daily/tasmax-poly-4"), 'tasmax-poly-4'))

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

        for clipping in [True, False]:
            for filepath in glob.glob(files.sharedpath("social/parameters/labor/NEWFOLDER/*.csvv")):
                basename = os.path.basename(filepath)[:-5]

                # Full Adaptation
                if check_doit(targetdir, basename, suffix):
                    print "Smart Farmer"
                    calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(filepath, 'impacts.labor.global20170216', weatherbundle, economicmodel, pvals[basename], clipping=clipping)

                    effectset.generate(targetdir, basename + ('-clipped' if clipping else '') + suffix, weatherbundle, calculation, "Extensive margin labor impacts, with interpolation and adaptation through interpolation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, result_callback=lambda reg, yr, res, calc: result_callback(reg, yr, res, calc, basename), push_callback=lambda reg, yr, app: push_callback(reg, int(yr) / 1000, app, baseline_get_predictors, basename), do_interpbins=False, diagnosefile=diagnosefile.replace('.csv', '-' + basename + '.csv') if diagnosefile else False)

                if config['do_farmers'] and not weatherbundle.is_historical():
                    # Lock in the values
                    pvals[basename].lock()

                    # Comatose Farmer
                    if check_doit(targetdir, basename + "-comatose" + ('-clipped' if clipping else ''), suffix):
                        print "Comatose Farmer"
                        calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(filepath, 'impacts.labor.global20170216', weatherbundle, economicmodel, pvals[basename], farmer='coma', clipping=clipping)
                        effectset.generate(targetdir, basename + "-comatose" + ('-clipped' if clipping else '') + suffix, weatherbundle, calculation, "Extensive margin labor impacts, with no adaptation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, result_callback=lambda reg, yr, res, calc: result_callback(reg, yr, res, calc, basename + '-coma'), push_callback=lambda reg, yr, app: push_callback(reg, int(yr) / 1000, app, baseline_get_predictors, basename), do_interpbins=False)

                    # Dumb Farmer
                    if check_doit(targetdir, basename + "-dumb" + ('-clipped' if clipping else ''), suffix):
                        print "Dumb Farmer"
                        calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(filepath, 'impacts.labor.global20170216', weatherbundle, economicmodel, pvals[basename], farmer='dumb', clipping=clipping)
                        effectset.generate(targetdir, basename + "-dumb" + ('-clipped' if clipping else '') + suffix, weatherbundle, calculation, "Extensive margin labor impacts, with interpolation and only environmental adaptation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, result_callback=lambda reg, yr, res, calc: result_callback(reg, yr, res, calc, basename + '-dumb'), push_callback=lambda reg, yr, app: push_callback(reg, int(yr) / 1000, app, baseline_get_predictors, basename), do_interpbins=False)
