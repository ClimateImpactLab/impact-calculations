import os, glob
from generate import weather, server, effectset, caller
from climate.dailyreader import YearlyBinnedWeatherReader

do_interpbins = True

def preload():
    from datastore import library
    library.get_data('mortality-deathrates', 'deaths/person')

climatebasedir = '/shares/gcp/climate/BCSD/aggregation/cmip5_bins/IR_level'
readercls = YearlyBinnedWeatherReader

def produce(targetdir, weatherbundle, economicmodel, get_model, pvals, do_only=None, country_specific=True, result_callback=None, push_callback=None, suffix='', do_farmers=False, do_65plus=True):
    if do_only is None or do_only == 'acp':
        # ACP response
        calculation, dependencies = caller.call_prepare('impacts.mortality.ACRA_mortality_temperature', weatherbundle, economicmodel, pvals['ACRA_mortality_temperature'])
        effectset.write_ncdf(targetdir, "ACPMortality", weatherbundle, calculation, None, "Mortality using the ACP response function.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, suffix=suffix)

    if do_only is None or do_only == 'interpolation':
        if result_callback is None:
            result_callback = lambda reg, yr, res, calc, mod: None
        if push_callback is None:
            push_callback = lambda reg, yr, app, predget: None

        #for filepath in ["/shares/gcp/social/parameters/mortality/predictors-space-all.csvv"]:
        #for filepath in glob.glob("/shares/gcp/social/parameters/mortality/mortality_single_stage_12092016/*.csvv"):
        for filepath in ["/shares/gcp/social/parameters/mortality/mortality_single_stage_12092016/global_interaction_no_popshare_BEST.csvv"]:
            # Full Adaptation
            calculation, dependencies, curve, baseline_get_predictors = caller.call_prepare_interp(filepath, 'impacts.mortality.mortality_csvv', weatherbundle, economicmodel, pvals[os.path.basename(filepath)])
            effectset.write_ncdf(targetdir, "InterpolatedMortality", weatherbundle, calculation, baseline_get_predictors, "Mortality impacts, with interpolation and adaptation through interpolation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, result_callback=lambda reg, yr, res, calc: result_callback(reg, yr, res, calc, 'all'), push_callback=lambda reg, yr, app: push_callback(reg, yr, app, baseline_get_predictors), do_interpbins=do_interpbins, suffix=suffix)

            if do_farmers and not weatherbundle.is_historical():
                # Lock in the values
                pvals[os.path.basename(filepath)].lock()

                # Comatose Farmer
                calculation, dependencies, curve, baseline_get_predictors = caller.call_prepare_interp(filepath, 'impacts.mortality.mortality_csvv_comatose', weatherbundle, economicmodel, pvals[os.path.basename(filepath)])
                effectset.write_ncdf(targetdir, "InterpolatedMortalityComatose", weatherbundle, calculation, baseline_get_predictors, "Mortality impacts, with interpolation but no adaptation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, result_callback=lambda reg, yr, res, calc: result_callback(reg, yr, res, calc, 'all-coma'), push_callback=lambda reg, yr, app: push_callback(reg, yr, app, baseline_get_predictors), suffix=suffix)

                # Dumb Farmer
                calculation, dependencies, curve, baseline_get_predictors = caller.call_prepare_interp(filepath, 'impacts.mortality.mortality_csvv_dumb', weatherbundle, economicmodel, pvals[os.path.basename(filepath)])
                effectset.write_ncdf(targetdir, "InterpolatedMortalityDumb", weatherbundle, calculation, baseline_get_predictors, "Mortality impacts, with interpolation and only environmental adaptation.", dependencies + weatherbundle.dependencies + economicmodel.dependencies, result_callback=lambda reg, yr, res, calc: result_callback(reg, yr, res, calc, 'all-dumb'), push_callback=lambda reg, yr, app: push_callback(reg, yr, app, baseline_get_predictors), suffix=suffix)

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
