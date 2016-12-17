import os, glob
from generate import weather, server, effectset, caller
from climate.discover import discover_variable, discover_derived_variable

def preload():
    pass

bundle_iterator = weather.iterate_combined_bundles(discover_variable('/shares/gcp/climate/BCSD/aggregation/cmip5/IR_level', 'tasmax'),
                                                   discover_derived_variable('/shares/gcp/climate/BCSD/aggregation/cmip5/IR_level', 'tasmax', 'power2'),
                                                   discover_derived_variable('/shares/gcp/climate/BCSD/aggregation/cmip5/IR_level', 'tasmax', 'power3'),
                                                   discover_derived_variable('/shares/gcp/climate/BCSD/aggregation/cmip5/IR_level', 'tasmax', 'power4'))

def produce(targetdir, weatherbundle, economicmodel, get_model, pvals, do_only=None, country_specific=True, result_callback=None, push_callback=None, suffix='', do_farmers=False, profile=False):
    if do_only is None or do_only == 'acp':
        pass

    if do_only is None or do_only == 'interpolation':
        if result_callback is None:
            result_callback = lambda reg, yr, res, calc, mod: None
        if push_callback is None:
            push_callback = lambda reg, yr, app, predget, mod: None

        for filepath in glob.glob("/shares/gcp/social/parameters/labor/*.csvv"):
            basename = os.path.basename(filepath)[:-5]

            # Full Adaptation
            calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp2(filepath, 'impacts.labor.global20161209', weatherbundle, economicmodel, pvals[basename], callback=lambda v, r, x, y: None)

            if profile:
                effectset.small_test(weatherbundle, calculation, None, num_regions=10)
                return
            else:
                effectset.write_ncdf(targetdir, basename, weatherbundle, calculation, None, "Extensive margin labor impacts, with interpolation and adaptation through interpolation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, result_callback=lambda reg, yr, res, calc: result_callback(reg, yr, res, calc, basename), push_callback=lambda reg, yr, app: push_callback(reg, yr / 1000, app, baseline_get_predictors, basename), do_interpbins=False, suffix=suffix)

