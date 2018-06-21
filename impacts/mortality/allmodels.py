import os, glob, traceback
import numpy as np
from impactlab_tools.utils import files
from adaptation import csvvfile
from generate import weather, effectset, caller, checks, agglib
from openest.generate.weatherslice import YearlyWeatherSlice
from climate.discover import discover_versioned, discover_variable
from datastore import agecohorts

def preload():
    from datastore import library
    library.get_data('mortality-deathrates', 'deaths/person')

def get_bundle_iterator(config):
    return weather.iterate_bundles(discover_tas_binned(files.sharedpath("climate/BCSD/aggregation/cmip5_bins_new/IR_level"), **config), **config)

def check_doit(targetdir, basename, suffix):
    filepath = os.path.join(targetdir, basename + suffix + '.nc4')
    if not os.path.exists(filepath):
        print "REDO: Cannot find", filepath, suffix
        return True

    # Check if has 100 valid years
    if not checks.check_result_100years(filepath):
        print "REDO: Incomplete", basename, suffix
        return True

    return False

def produce(targetdir, weatherbundle, economicmodel, pvals, config, push_callback=None, suffix='', profile=False, diagnosefile=False):
    print config['do_only']

    if config['do_only'] is None or config['do_only'] == 'interpolation':
        if push_callback is None:
            push_callback = lambda reg, yr, app, predget, mod: None

        assert 'csvvfile' in config:
        csvvfiles = [files.sharedpath(config['csvvfile'])]
            
        for filepath in csvvfiles:
            basename = os.path.basename(filepath)[:-5]
            print basename

            module = 'impacts.mortality.ols_binned'

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
                    calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(subcsvv, module, weatherbundle, economicmodel, pvals[subbasename], config=config)

                    effectset.generate(targetdir, subbasename + suffix, weatherbundle, calculation, "Mortality impacts, with interpolation and adaptation through interpolation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, push_callback=lambda reg, yr, app: push_callback(reg, yr, app, baseline_get_predictors, subbasename), diagnosefile=diagnosefile.replace('.csv', '-' + subbasename + '.csv') if diagnosefile else False)

                    if profile:
                        return

                if config['do_farmers'] and not weatherbundle.is_historical():
                    # Lock in the values
                    pvals[subbasename].lock()

                    # Comatose Farmer
                    if check_doit(targetdir, subbasename + "-noadapt", suffix):
                        calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(subcsvv, module, weatherbundle, economicmodel, pvals[subbasename], farmer='coma', config=config)

                        effectset.generate(targetdir, subbasename + "-noadapt" + suffix, weatherbundle, calculation, "Mortality impacts, with interpolation but no adaptation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, push_callback=lambda reg, yr, app: push_callback(reg, yr, app, baseline_get_predictors, subbasename + '-noadapt'))

                    # Dumb Farmer
                    if check_doit(targetdir, subbasename + "-incadapt", suffix):
                        calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(subcsvv, module, weatherbundle, economicmodel, pvals[subbasename], farmer='dumb', config=config)

                        effectset.generate(targetdir, subbasename + "-incadapt" + suffix, weatherbundle, calculation, "Mortality impacts, with interpolation and only environmental adaptation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, push_callback=lambda reg, yr, app: push_callback(reg, yr, app, baseline_get_predictors, subbasename + '-incadapt'))

            # Combine the ages
            try:
                for assumption in ['', '-noadapt', '-incadapt']:
                    if assumption != '':
                        if not config['do_farmers'] or weatherbundle.is_historical():
                            continue
                    halfweight = agecohorts.SpaceTimeBipartiteData(1981, 2100, None)
                    basenames = [basename + '-' + agegroup + assumption + suffix for agegroup in agegroups]
                    get_stweights = [lambda year0, year1: halfweight.load(year0, year1, economicmodel.model, economicmodel.scenario, 'age0-4'), lambda year0, year1: halfweight.load(year0, year1, economicmodel.model, economicmodel.scenario, 'age5-64'), lambda year0, year1: halfweight.load(year0, year1, economicmodel.model, economicmodel.scenario, 'age65+')]
                    if check_doit(targetdir, basename + '-combined' + assumption, suffix):
                        agglib.combine_results(targetdir, basename + '-combined' + assumption, basenames, get_stweights, "Combined mortality across age-groups for " + basename, suffix=suffix)
            except Exception as ex:
                print "TO FIX: Combining failed."
                traceback.print_exc()

    if 'csvvfile' not in config:
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
            try:
                calculation, dependencies = caller.call_prepare_interp(filepath, module, weatherbundle, economicmodel, pvals[basename], config=config)

                effectset.generate(targetdir, basename + suffix, weatherbundle, calculation, "India-model mortality impacts for all ages.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, diagnosefile=diagnosefile.replace('.csv', '-' + basename + '.csv') if diagnosefile else False)
            except Exception as ex:
                print ex

def produce_external(targetdir, weatherbundle, economicmodel, pvals, config, suffix=''):
    if config['do_only'] is None or config['do_only'] == 'acp':
        # ACP response
        calculation, dependencies = caller.call_prepare('impacts.mortality.external.ACRA_mortality_temperature', weatherbundle, economicmodel, pvals['ACRA_mortality_temperature'], config=config)
        effectset.generate(targetdir, "ACPMortality" + suffix, weatherbundle, calculation, "Mortality using the ACP response function.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config)


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
            calculation, dependencies = caller.call_prepare('impacts.mortality.external.' + gcpid, weatherbundle, economicmodel, pvals[gcpid], config=config)
            effectset.generate(targetdir, gcpid + suffix, weatherbundle, calculation, "See https://bitbucket.org/ClimateImpactLab/socioeconomics/wiki/HealthModels#rst-header-" + gcpid.replace('_', '-').lower() + " for more information.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, config, filter_region=filter_region, subset=subset)
