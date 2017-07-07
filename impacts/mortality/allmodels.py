import os, glob
import numpy as np
from impactlab_tools.utils import files
from adaptation import csvvfile
from generate import weather, server, effectset, caller, checks, agglib
from openest.generate.weatherslice import YearlyWeatherSlice
from climate.discover import discover_vesioned
from datastore import agecohorts

def preload():
    from datastore import library
    library.get_data('mortality-deathrates', 'deaths/person')

rcp_only = 'rcp85'

def get_bundle_iterator(config):
    climdir = files.sharedpath('climate/BCSD/aggregation/cmip5/IR_level')
    return weather.iterate_combined_bundles(discover_vesioned("/shares/gcp/climate/BCSD/Mortality/polynomial-fix/hierid/popwt/daily/tas", 'tas', '1.1'),
                                            discover_vesioned("/shares/gcp/climate/BCSD/Mortality/polynomial-fix/hierid/popwt/daily/tas-poly-2", 'tas-poly-2', '1.1'),
                                            discover_vesioned("/shares/gcp/climate/BCSD/Mortality/polynomial-fix/hierid/popwt/daily/tas-poly-3", 'tas-poly-3', '1.1'),
                                            discover_vesioned("/shares/gcp/climate/BCSD/Mortality/polynomial-fix/hierid/popwt/daily/tas-poly-4", 'tas-poly-4', '1.1'),
                                            discover_vesioned("/shares/gcp/climate/BCSD/Mortality/polynomial-fix/hierid/popwt/daily/tas-poly-5", 'tas-poly-5', '1.1'))

def check_doit(targetdir, basename, suffix):
    filepath = effectset.get_ncdf_path(targetdir, basename, suffix)
    if not os.path.exists(filepath):
        print "REDO: Cannot find", filepath
        return True

    # Check if has 100 valid years
    if not checks.check_result_100years(filepath):
        print "REDO: Incomplete", basename, suffix
        return True

    return False

def produce(targetdir, weatherbundle, economicmodel, pvals, config, result_callback=None, push_callback=None, suffix='', profile=False, diagnosefile=False):
    print config['do_only']

    if config['do_only'] is None or config['do_only'] == 'interpolation':
        if result_callback is None:
            result_callback = lambda reg, yr, res, calc, mod: None
        if push_callback is None:
            push_callback = lambda reg, yr, app, predget, mod: None

        for filepath in glob.glob(files.sharedpath("social/parameters/mortality/Diagnostics_Apr17/*.csvv")):
            basename = os.path.basename(filepath)[:-5]
            print basename

            if 'CSpline' in basename:
                numpreds = 5
                module = 'impacts.mortality.ols_cubic_spline'
                minpath_suffix = '-splinemins'
            else:
                if 'POLY-5' in basename:
                    numpreds = 5
                elif 'POLY-4' in basename:
                    numpreds = 4
                else:
                    ValueError("Unknown number of predictors")
                module = 'impacts.mortality.ols_polynomial'
                minpath_suffix = '-polymins'

            # Split into age groups and lock in q-draw
            csvv = csvvfile.read(filepath)
            csvvfile.collapse_bang(csvv, pvals[basename].get_seed())

            agegroups = ['young', 'older', 'oldest']
            for ageii in range(len(agegroups)):
                subcsvv = csvvfile.subset(csvv, 3 * numpreds * ageii + np.arange(3 * numpreds))
                subbasename = basename + '-' + agegroups[ageii]
                caller.callinfo = dict(minpath=os.path.join(targetdir, subbasename + minpath_suffix + '.csv'))

                # Full Adaptation
                if check_doit(targetdir, subbasename, suffix):
                    print "Smart Farmer"
                    calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(subcsvv, module, weatherbundle, economicmodel, pvals[subbasename])

                    effectset.generate(targetdir, subbasename, weatherbundle, calculation, None, "Mortality impacts, with interpolation and adaptation through interpolation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, result_callback=lambda reg, yr, res, calc: result_callback(reg, yr, res, calc, subbasename), push_callback=lambda reg, yr, app: push_callback(reg, yr, app, baseline_get_predictors, subbasename), suffix=suffix, diagnosefile=diagnosefile.replace('.csv', '-' + subbasename + '.csv') if diagnosefile else False)

                if config['do_farmers'] and not weatherbundle.is_historical():
                    # Lock in the values
                    pvals[subbasename].lock()

                    # Comatose Farmer
                    if check_doit(targetdir, subbasename + "-noadapt", suffix):
                        calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(subcsvv, module, weatherbundle, economicmodel, pvals[subbasename], farmer='coma')

                        effectset.generate(targetdir, subbasename + "-noadapt", weatherbundle, calculation, None, "Mortality impacts, with interpolation but no adaptation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, result_callback=lambda reg, yr, res, calc: result_callback(reg, yr, res, calc, subbasename + '-noadapt'), push_callback=lambda reg, yr, app: push_callback(reg, yr, app, baseline_get_predictors, subbasename + '-noadapt'), suffix=suffix)

                    # Dumb Farmer
                    if check_doit(targetdir, subbasename + "-incadapt", suffix):
                        calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(subcsvv, module, weatherbundle, economicmodel, pvals[subbasename], farmer='dumb')

                        effectset.generate(targetdir, subbasename + "-incadapt", weatherbundle, calculation, None, "Mortality impacts, with interpolation and only environmental adaptation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, result_callback=lambda reg, yr, res, calc: result_callback(reg, yr, res, calc, subbasename + '-incadapt'), push_callback=lambda reg, yr, app: push_callback(reg, yr, app, baseline_get_predictors, subbasename + '-incadapt'), suffix=suffix)

            # Combine the ages
            # try:
            #     for assumption in ['', '-noadapt', '-incadapt']:
            #         if assumption != '':
            #             if config['do_farmers'] and not weatherbundle.is_historical():
            #                 continue
            #         halfweight = agecohorts.SpaceTimeBipartiteData(1981, 2100, None)
            #         basenames = [basename + '-' + agegroup + assumption for agegroup in agegroups]
            #         get_stweights = [lambda year0, year1: halfweight.load_population(year0, year1, economicmodel.model, economicmodel.scenario, 'age0-4'), lambda year0, year1: halfweight.load_population(year0, year1, economicmodel.model, economicmodel.scenario, 'age5-64'), lambda year0, year1: halfweight.load_population(year0, year1, economicmodel.model, economicmodel.scenario, 'age65+')]
            #         if check_doit(targetdir, basename + '-combined' + assumption, suffix):
            #             agglib.combine_results(targetdir, basename + '-combined' + assumption, basenames, get_stweights, "Combined mortality across age-groups for " + basename, suffix=suffix)
            # except Exception as ex:
            #     print "TO FIX: Combining failed."
            #     print ex

    produce_india(targetdir, weatherbundle, economicmodel, pvals, config, suffix=suffix, diagnosefile=diagnosefile)
    produce_external(targetdir, weatherbundle, economicmodel, pvals, config, suffix=suffix)

def produce_india(targetdir, weatherbundle, economicmodel, pvals, config, suffix='', diagnosefile=False):
    for filepath in glob.glob(files.sharedpath("social/parameters/mortality/India/*.csvv")):
        basename = os.path.basename(filepath)[:-5]
        print basename

        if 'cubic_splines' in basename:
            numpreds = 5
            module = 'impacts.mortality.ols_cubic_spline_india'
            minpath_suffix = '-splinemins'
        else:
            if 'POLY-5' in basename:
                numpreds = 5
            elif 'POLY-4' in basename:
                numpreds = 4
            else:
                ValueError("Unknown number of predictors")
            module = 'impacts.mortality.ols_polynomial_india'
            minpath_suffix = '-polymins'

        if check_doit(targetdir, basename, suffix):
            print "India result"
            calculation, dependencies = caller.call_prepare_interp(filepath, module, weatherbundle, economicmodel, pvals[basename])

            effectset.generate(targetdir, basename, weatherbundle, calculation, None, "India-model mortality impacts for all ages.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, suffix=suffix, diagnosefile=diagnosefile.replace('.csv', '-' + basename + '.csv') if diagnosefile else False)

def produce_external(targetdir, weatherbundle, economicmodel, pvals, config, suffix=''):
    if config['do_only'] is None or config['do_only'] == 'acp':
        # ACP response
        calculation, dependencies = caller.call_prepare('impacts.mortality.external.ACRA_mortality_temperature', weatherbundle, economicmodel, pvals['ACRA_mortality_temperature'])
        effectset.generate(targetdir, "ACPMortality", weatherbundle, calculation, None, "Mortality using the ACP response function.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, suffix=suffix)


    if config['do_only'] is None or config['do_only'] == 'country':
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
            effectset.generate(targetdir, gcpid, weatherbundle, calculation, None, "See https://bitbucket.org/ClimateImpactLab/socioeconomics/wiki/HealthModels#rst-header-" + gcpid.replace('_', '-').lower() + " for more information.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, filter_region=filter_region, subset=subset, suffix=suffix)
