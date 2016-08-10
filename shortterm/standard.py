import glob, os
from impacts.conflict import standard
from impacts.weather import MultivariateHistoricalWeatherBundle
from adaptation.econmodel import iterate_econmodels
import curvegen, effectset

def produce(targetdir, weatherbundle, qvals, do_only=None, suffix=''):
    historicalbundle = MultivariateHistoricalWeatherBundle("/shares/gcp/BCSD/grid2reg/cmip5/historical/CCSM4/{0}/{0}_day_aggregated_historical_r1i1p1_CCSM4_{1}.nc", 1991, 2005, ['pr', 'tas'])
    model, scenario, econmodel = (mse for mse in iterate_econmodels() if mse[0] == 'OECD Env-Growth').next()

    # if do_only is None or do_only == 'acp':
    #     # ACP response
    #     calculation, dependencies = caller.call_prepare('impacts.conflict.ACRA_violentcrime', weatherbundle, qvals['ACRA_violentcrime'])
    #     effectset.write_ncdf(targetdir, "ViolentCrime", weatherbundle, calculation, None, "Violent crime using the ACP response function.", dependencies + weatherbundle.dependencies, suffix=suffix)
    #     calculation, dependencies = caller.call_prepare('impacts.conflict.ACRA_propertycrime', weatherbundle, qvals['ACRA_propertycrime'])
    #     effectset.write_ncdf(targetdir, "PropertyCrime", weatherbundle, calculation, None, "Property crime using the ACP response function.", dependencies + weatherbundle.dependencies, suffix=suffix)

    if do_only is None or do_only == 'interpolation':
        predgen = curvegen.TemperaturePrecipitationPredictorator(historicalbundle, econmodel, 15, 3, 2005)
        baseline_get_predictors = predgen.get_baseline

        ## Full interpolation
        for filepath in glob.glob("/shares/gcp/data/adaptation/conflict/*.csvv"):
            basename = os.path.basename(filepath)[:-5]
            print basename

            thisqvals = qvals[basename]
            calculation, dependencies = standard.prepare_csvv(filepath, thisqvals)

            effectset.write_ncdf(thisqvals['weather'], targetdir, basename, weatherbundle, calculation, baseline_get_predictors, "Interpolated response for " + basename + ".", dependencies + weatherbundle.dependencies, suffix=suffix)
