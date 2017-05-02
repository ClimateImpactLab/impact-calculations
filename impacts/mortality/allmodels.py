import os, glob
from impactlab_tools.utils import files
from generate import weather, server, effectset, caller, checks
from climate.discover import discover_yearly_variable, discover_yearly_array

do_interpbins = True

def preload():
    from datastore import library
    library.get_data('mortality-deathrates', 'deaths/person')

rcp_only = 'rcp85'

def get_bundle_iterator():
    return weather.iterate_combined_bundles(discover_yearly_variable(files.sharedpath('climate/BCSD/aggregation/cmip5_new/IR_level'),
                                                                     'cubic_spline_tas', 'tas_sum', rcp_only=rcp_only),
                                            discover_yearly_array(files.sharedpath('climate/BCSD/aggregation/cmip5_new/IR_level'),
                                                                  'cubic_spline_tas', 'spline_variables',
                                                                  ['spline_variables-%d' % ii for ii in range(1, 7)], rcp_only=rcp_only))

def check_doit(redocheck, targetdir, basename, suffix):
    if not redocheck:
        print "REDO: Missing", basename, suffix
        return True

    filepath = effectset.get_ncdf_path(targetdir, basename, suffix)
    if not os.path.exists(filepath):
        print "REDO: Cannot find", filepath
        return True

    # Check if has 100 valid years
    if not checks.check_result_100years(filepath):
        print "REDO: Incomplete", basename, suffix
        return True

    return False

def produce(targetdir, weatherbundle, economicmodel, get_model, pvals, do_only=None, country_specific=True, result_callback=None, push_callback=None, suffix='', do_farmers=False, do_65plus=True, profile=False, redocheck=None, diagnosefile=False):
    print do_only
    if do_only is None or do_only == 'acp':
        # ACP response
        calculation, dependencies = caller.call_prepare('impacts.mortality.ACRA_mortality_temperature', weatherbundle, economicmodel, pvals['ACRA_mortality_temperature'])
        effectset.write_ncdf(targetdir, "ACPMortality", weatherbundle, calculation, None, "Mortality using the ACP response function.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, suffix=suffix)

    if do_only is None or do_only == 'interpolation':
        if result_callback is None:
            result_callback = lambda reg, yr, res, calc, mod: None
        if push_callback is None:
            push_callback = lambda reg, yr, app, predget, mod: None

        #for filepath in glob.glob(files.sharedpath("social/parameters/mortality/mortality_splines_03162017/*2factors*.csvv")):
        for filepath in glob.glob(files.sharedpath("social/parameters/mortality/MLE_splines_03212017/*.csvv")):
            basename = os.path.basename(filepath)[:-5]
            print basename

            # Full Adaptation
            if check_doit(redocheck, targetdir, basename, suffix):
                print "Smart Farmer"
                caller.callinfo = dict(splineminpath=os.path.join(targetdir, basename + '-splinemins.csv'))
                calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(filepath, 'impacts.mortality.mle_cubic_spline', weatherbundle, economicmodel, pvals[basename])

                if profile:
                    effectset.small_test(weatherbundle, calculation, baseline_get_predictors, num_regions=10)
                    return
                else:
                    effectset.write_ncdf(targetdir, basename, weatherbundle, calculation, None, "Mortality impacts, with interpolation and adaptation through interpolation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, result_callback=lambda reg, yr, res, calc: result_callback(reg, yr, res, calc, basename), push_callback=lambda reg, yr, app: push_callback(reg, yr, app, baseline_get_predictors, basename), do_interpbins=do_interpbins, suffix=suffix, diagnosefile=diagnosefile.replace('.csv', '-' + basename + '.csv') if diagnosefile else False)

            if do_farmers and not weatherbundle.is_historical():
                # Lock in the values
                pvals[basename].lock()

                # Comatose Farmer
                if check_doit(redocheck, targetdir, basename + "-comatose", suffix):
                    calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(filepath, 'impacts.mortality.mle_cubic_spline', weatherbundle, economicmodel, pvals[basename], farmer='coma')

                    effectset.write_ncdf(targetdir, basename + "-comatose", weatherbundle, calculation, None, "Mortality impacts, with interpolation but no adaptation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, result_callback=lambda reg, yr, res, calc: result_callback(reg, yr, res, calc, basename + '-coma'), push_callback=lambda reg, yr, app: push_callback(reg, yr, app, baseline_get_predictors, basename + '-coma'), suffix=suffix)

                # Dumb Farmer
                if check_doit(redocheck, targetdir, basename + "-dumb", suffix):
                    calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(filepath, 'impacts.mortality.mle_cubic_spline', weatherbundle, economicmodel, pvals[basename], farmer='dumb')

                    effectset.write_ncdf(targetdir, basename + "-dumb", weatherbundle, calculation, None, "Mortality impacts, with interpolation and only environmental adaptation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, result_callback=lambda reg, yr, res, calc: result_callback(reg, yr, res, calc, basename + '-dumb'), push_callback=lambda reg, yr, app: push_callback(reg, yr, app, baseline_get_predictors, basename + '-dumb'), suffix=suffix)

    if do_only is None or do_only == 'country':
        # Other individual estimates
        for gcpid in ['DM2009_USA_national_mortality_all', 'BCDGS2013_USA_national_mortality_all', 'BCDGS2013_USA_national_mortality_65plus', 'GHA2003_BRA_national_mortality_all', 'GHA2003_BRA_national_mortality_65plus', 'B2012_USA_national_mortality_all', 'VSMPMCL2004_FRA_national_mortality_all', 'InternalAnalysis_BRA_national_mortality_all', 'InternalAnalysis_BRA_national_mortality_65plus', 'InternalAnalysis_MEX_national_mortality_all', 'InternalAnalysis_MEX_national_mortality_65plus', 'InternalAnalysis_CHN_national_mortality_all', 'InternalAnalysis_FRA_national_mortality_all', 'InternalAnalysis_FRA_national_mortality_65plus', 'InternalAnalysis_IND_national_mortality_all', 'InternalAnalysis_USA_national_mortality_all', 'InternalAnalysis_USA_national_mortality_65plus']:
            filter_region = None
            subset = None
            if country_specific:
                if 'USA' in gcpid:
                    filter_region = lambda region: region[0:3] == 'USA'
                    subset = 'USA'
                elif 'BRA' in gcpid:
                    filter_region = lambda region: region[0:3] == 'BRA'
                    subset = 'BRA'
                elif 'FRA' in gcpid:
                    filter_region = lambda region: region[0:3] == 'FRA'
                    subset = 'FRA'
                elif 'MEX' in gcpid:
                    filter_region = lambda region: region[0:3] == 'MEX'
                    subset = 'MEX'
                elif 'CHN' in gcpid:
                    filter_region = lambda region: region[0:3] == 'CHN'
                    subset = 'CHN'
                elif 'IND' in gcpid:
                    filter_region = lambda region: region[0:3] == 'IND'
                    subset = 'IND'
                else:
                    assert False, "Unknown filter region."

            # Removed DG2011_USA_national_mortality_65plus: Amir considers unreliable
            calculation, dependencies = caller.call_prepare('impacts.mortality.' + gcpid, weatherbundle, economicmodel, pvals[gcpid])
            effectset.write_ncdf(targetdir, gcpid, weatherbundle, calculation, None, "See https://bitbucket.org/ClimateImpactLab/socioeconomics/wiki/HealthModels#rst-header-" + gcpid.replace('_', '-').lower() + " for more information.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, filter_region=filter_region, subset=subset, suffix=suffix)
