import os, glob
from impactlab_tools.utils import files
from generate import weather, server, effectset, caller, checks
from climate.discover import discover_yearly_variable, discover_yearly_array

def preload():
    from datastore import library
    library.get_data('mortality-deathrates', 'deaths/person')

rcp_only = 'rcp85'

def get_bundle_iterator():
    def time_convert(times):
        allyears = np.array(map(int, np.array(times) // 1000))
        years, indexes = np.unique(allyears, return_index=True)
        return allyears[np.sort(indexes)] # make sure in order

    return weather.iterate_combined_bundles(discover_convert(discover_variable(files.sharedpath('climate/BCSD/aggregation/cmip5/IR_level'),
                                                                               'tas', withyear=True, rcp_only='rcp85'),
                                                             time_convert, YearlyWeatherSlice.convert),
                                            discover_derived_variable(files.sharedpath('climate/BCSD/aggregation/cmip5/IR_level'),
                                                                      'tas', 'power2', withyear=False, rcp_only=rcp_only),
                                            discover_derived_variable(files.sharedpath('climate/BCSD/aggregation/cmip5/IR_level'),
                                                                      'tas', 'power3', withyear=False, rcp_only=rcp_only),
                                            discover_derived_variable(files.sharedpath('climate/BCSD/aggregation/cmip5/IR_level'),
                                                                      'tas', 'power4', withyear=False, rcp_only=rcp_only))

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

def produce(targetdir, weatherbundle, economicmodel, pvals, do_only=None, country_specific=True, result_callback=None, push_callback=None, suffix='', do_farmers=False, do_65plus=True, profile=False, redocheck=None, diagnosefile=False):
    print do_only

    if do_only is None or do_only == 'interpolation':
        if result_callback is None:
            result_callback = lambda reg, yr, res, calc, mod: None
        if push_callback is None:
            push_callback = lambda reg, yr, app, predget, mod: None

        for filepath in glob.glob(files.sharedpath("social/parameters/mortality/Diagnostics_Apr17/*.csvv")):
            basename = os.path.basename(filepath)[:-5]
            print basename

            # Split into age groups and lock in q-draw
            csvv = csvvfile.read(filepath)
            csvvfile.collapse_bang(csvv)

            agegroups = ['lt5', '5to64', 'gt64']
            for ageii in range(len(agegroups)):
                subcsvv = csvvfile.subset(csvv, 12 * ageii + np.arange(12))
                subbasename = basename + '-' + agegroups[ageii]
            
                # Full Adaptation
                if check_doit(redocheck, targetdir, subbasename, suffix):
                    print "Smart Farmer"
                    calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(subcsvv, 'impacts.mortality.ols_polynomial', weatherbundle, economicmodel, pvals[subbasename])

                    if profile:
                        effectset.small_test(weatherbundle, calculation, baseline_get_predictors, num_regions=10)
                        return
                    else:
                        effectset.write_ncdf(targetdir, subbasename, weatherbundle, calculation, None, "Mortality impacts, with interpolation and adaptation through interpolation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, result_callback=lambda reg, yr, res, calc: result_callback(reg, yr, res, calc, subbasename), push_callback=lambda reg, yr, app: push_callback(reg, yr, app, baseline_get_predictors, subbasename), suffix=suffix, diagnosefile=diagnosefile.replace('.csv', '-' + subbasename + '.csv') if diagnosefile else False)

                if do_farmers and not weatherbundle.is_historical():
                    # Lock in the values
                    pvals[subbasename].lock()

                    # Comatose Farmer
                    if check_doit(redocheck, targetdir, subbasename + "-comatrump", suffix):
                        calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(subcsvv, 'impacts.mortality.ols_polynomial', weatherbundle, economicmodel, pvals[subbasename], farmer='coma')

                        effectset.write_ncdf(targetdir, subbasename + "-comatrump", weatherbundle, calculation, None, "Mortality impacts, with interpolation but no adaptation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, result_callback=lambda reg, yr, res, calc: result_callback(reg, yr, res, calc, subbasename + '-comatrump'), push_callback=lambda reg, yr, app: push_callback(reg, yr, app, baseline_get_predictors, subbasename + '-comatrump'), suffix=suffix)

                    # Dumb Farmer
                    if check_doit(redocheck, targetdir, subbasename + "-dumgop", suffix):
                        calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(subcsvv, 'impacts.mortality.ols_polynomial', weatherbundle, economicmodel, pvals[subbasename], farmer='dumb')

                        effectset.write_ncdf(targetdir, subbasename + "-dumgop", weatherbundle, calculation, None, "Mortality impacts, with interpolation and only environmental adaptation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, result_callback=lambda reg, yr, res, calc: result_callback(reg, yr, res, calc, subbasename + '-dumgop'), push_callback=lambda reg, yr, app: push_callback(reg, yr, app, baseline_get_predictors, subbasename + '-dumgop'), suffix=suffix)

    produce_external(targetdir, weatherbundle, exconomicmodel, pvals, do_only=do_only, country_specific=country_specific, suffix=suffix)
                        
def produce_external(targetdir, weatherbundle, exconomicmodel, pvals, do_only=None, country_specific=True, suffix=''):
    if do_only is None or do_only == 'acp':
        # ACP response
        calculation, dependencies = caller.call_prepare('impacts.mortality.external.ACRA_mortality_temperature', weatherbundle, economicmodel, pvals['ACRA_mortality_temperature'])
        effectset.write_ncdf(targetdir, "ACPMortality", weatherbundle, calculation, None, "Mortality using the ACP response function.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, suffix=suffix)

                        
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
            calculation, dependencies = caller.call_prepare('impacts.mortality.external.' + gcpid, weatherbundle, economicmodel, pvals[gcpid])
            effectset.write_ncdf(targetdir, gcpid, weatherbundle, calculation, None, "See https://bitbucket.org/ClimateImpactLab/socioeconomics/wiki/HealthModels#rst-header-" + gcpid.replace('_', '-').lower() + " for more information.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, filter_region=filter_region, subset=subset, suffix=suffix)
