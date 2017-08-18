import os, glob
from impactlab_tools.utils import files
from generate import weather, effectset, caller, checks
from climate.discover import discover_versioned

def preload():
    pass

def get_bundle_iterator(config):
    reorder = ('filter_region' in config)
    return weather.iterate_bundles(discover_versioned(files.sharedpath("climate/BCSD/hierid/popwt/daily/tasmax"), 'tasmax', reorder=reorder),
                                   discover_versioned(files.sharedpath("climate/BCSD/hierid/popwt/daily/tasmax-poly-2"), 'tasmax-poly-2', reorder=reorder),
                                   discover_versioned(files.sharedpath("climate/BCSD/hierid/popwt/daily/tasmax-poly-3"), 'tasmax-poly-3', reorder=reorder),
                                   discover_versioned(files.sharedpath("climate/BCSD/hierid/popwt/daily/tasmax-poly-4"), 'tasmax-poly-4', reorder=reorder))

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

def produce(targetdir, weatherbundle, economicmodel, pvals, config, push_callback=None, suffix='', profile=False, diagnosefile=False):
    if config['do_only'] is None or config['do_only'] == 'acp':
        pass

    if config['do_only'] is None or config['do_only'] == 'interpolation':
        if push_callback is None:
            push_callback = lambda reg, yr, app, predget, mod: None

        for clipping in [True, False]:
            for filepath in glob.glob(files.sharedpath("social/parameters/labor/csvvs/*.csvv")):
                basename = os.path.basename(filepath)[:-5]
                fullbasename = basename + ('-clipped' if clipping else '')

                # Full Adaptation
                if check_doit(targetdir, fullbasename, suffix):
                    print "Smart Farmer"
                    calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(filepath, 'impacts.labor.global20170809', weatherbundle, economicmodel, pvals[basename], clipping=clipping)

                    effectset.generate(targetdir, fullbasename + suffix, weatherbundle, calculation, "Extensive margin labor impacts, with interpolation and adaptation through interpolation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, push_callback=lambda reg, yr, app: push_callback(reg, yr, app, baseline_get_predictors, fullbasename), diagnosefile=diagnosefile.replace('.csv', '-' + fullbasename + '.csv') if diagnosefile else False)

                if config['do_farmers'] and not weatherbundle.is_historical():
                    # Lock in the values
                    pvals[basename].lock()

                    # Comatose Farmer
                    if check_doit(targetdir, fullbasename + "-noadapt", suffix):
                        print "Comatose Farmer"
                        calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(filepath, 'impacts.labor.global20170809', weatherbundle, economicmodel, pvals[basename], farmer='coma', clipping=clipping)
                        effectset.generate(targetdir, fullbasename + "-noadapt" + suffix, weatherbundle, calculation, "Extensive margin labor impacts, with no adaptation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, push_callback=lambda reg, yr, app: push_callback(reg, yr, app, baseline_get_predictors, fullbasename))

                    # Dumb Farmer
                    if check_doit(targetdir, fullbasename + "-incadapt", suffix):
                        print "Dumb Farmer"
                        calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(filepath, 'impacts.labor.global20170809', weatherbundle, economicmodel, pvals[basename], farmer='dumb', clipping=clipping)
                        effectset.generate(targetdir, fullbasename + "-incadapt" + suffix, weatherbundle, calculation, "Extensive margin labor impacts, with interpolation and only environmental adaptation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, push_callback=lambda reg, yr, app: push_callback(reg, yr, app, baseline_get_predictors, fullbasename))
