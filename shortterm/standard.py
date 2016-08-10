from impacts.conflict import standard

def produce(targetdir, weatherbundle, qvals, do_only=None):
    if do_only is None or do_only == 'acp':
        # ACP response
        calculation, dependencies = caller.call_prepare('impacts.conflict.ACRA_violentcrime', weatherbundle, qvals['ACRA_violentcrime'])
        effectset.write_ncdf(targetdir, "ViolentCrime", weatherbundle, calculation, None, "Violent crime using the ACP response function.", dependencies + weatherbundle.dependencies, suffix=suffix)

        calculation, dependencies = caller.call_prepare('impacts.conflict.ACRA_propertycrime', weatherbundle, qvals['ACRA_propertycrime'])
        effectset.write_ncdf(targetdir, "PropertyCrime", weatherbundle, calculation, None, "Property crime using the ACP response function.", dependencies + weatherbundle.dependencies, suffix=suffix)

    if do_only is None or do_only == 'interpolation':
        baseline_get_predictors = TemperaturePrecipitationPredictorator(historicalbundle, econmodel, 15, 15, 2005)

        ## Full interpolation
        calculation, dependencies = standard.prepare_csvv("/shares/gcp/data/adaptation/conflict/group_tp3_semur_auto.csvv", qvals['intergroup'])

        effectset.write_ncdf(targetdir, "InterpolatedInterpersonal", weatherbundle, calculation, baseline_get_predictors, "Interpolated response for interpersonal crime.", dependencies + weatherbundle.dependencies, suffix=suffix)

        calculation, dependencies, curve, baseline_get_predictors = caller.call_prepare('adaptation.interpolate', weatherbundle, qvals['interpolated_intergroup'])
        effectset.write_ncdf(targetdir, "InterpolatedIntergroup", weatherbundle, calculation, baseline_get_predictors, "Interpolated response for intergroup crime.", dependencies + weatherbundle.dependencies, suffix=suffix)
