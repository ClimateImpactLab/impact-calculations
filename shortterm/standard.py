from impacts.conflict import standard
from impacts.weather import MultivariateHistoricalWeatherBundle
from adaptation.econmodel import SSPEconomicModel

def produce(targetdir, weatherbundle, qvals, do_only=None):
    historicalbundle = MultivariateHistoricalWeatherBundle("/shares/gcp/BCSD/grid2reg/cmip5/historical/CCSM4/{0}/{0}_day_aggregated_historical_r1i1p1_CCSM4_{1}.nc", 1991, 2005, ['pr', 'tas'])
    econmodel = (mse for mse in iterate_econmodels() if mse[1] == 'OECD Env-Growth').next()

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
