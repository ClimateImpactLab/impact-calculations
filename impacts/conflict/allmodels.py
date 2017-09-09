import glob, os, csv
from generate.weather import SingleWeatherBundle
from climate.dailyreader import DailyWeatherReader
from adaptation.econmodel import iterate_econmodels
from shortterm import weather, curvegen, effectset
from climate import forecasts, forecastreader
import country

def get_bundle(qvals):
    tbundle = weather.ForecastBundle(forecastreader.MonthlyZScoreForecastOTFReader(forecasts.temp_path, forecasts.temp_climate_path, 'mean', qvals['tmean']))
    pbundle = weather.ForecastBundle(forecastreader.MonthlyStochasticForecastReader(forecasts.prcp_path, 'prcp', qvals['pmean']))
    weatherbundle = weather.CombinedBundle([tbundle, pbundle])

    return weatherbundle

def produce(targetdir, weatherbundle, qvals, do_only=None, suffix=''):
    historicalbundle = SingleWeatherBundle(DailyWeatherReader("/shares/gcp/climate/BCSD/aggregation/cmip5/IR_level/historical/CCSM4/tas/tas_day_aggregated_historical_r1i1p1_CCSM4_%d.nc", 1991, 'tas'), 'historical', 'CCSM4')
    model, scenario, econmodel = (mse for mse in iterate_econmodels() if mse[0] == 'high').next()

    # if do_only is None or do_only == 'acp':
    #     # ACP response
    #     calculation, dependencies = caller.call_prepare('impacts.conflict.ACRA_violentcrime', weatherbundle, qvals['ACRA_violentcrime'])
    #     effectset.write_ncdf(targetdir, "ViolentCrime" + suffix, weatherbundle, calculation, None, "Violent crime using the ACP response function.", dependencies + weatherbundle.dependencies)
    #     calculation, dependencies = caller.call_prepare('impacts.conflict.ACRA_propertycrime', weatherbundle, qvals['ACRA_propertycrime'])
    #     effectset.write_ncdf(targetdir, "PropertyCrime" + suffix, weatherbundle, calculation, None, "Property crime using the ACP response function.", dependencies + weatherbundle.dependencies)

    if do_only is None or do_only == 'interpolation':
        predgen1 = curvegen.WeatherPredictorator(historicalbundle, econmodel, 15, 3, 2005)

        ## Full interpolation
        for filepath in glob.glob("/shares/gcp/social/parameters/conflict/hierarchical_08102017/*.csvv"):
            basename = os.path.basename(filepath)[:-5]

            predicted_betas = {}
            def betas_callback(variable, region, predictors, betas):
                if region in predicted_betas:
                    predicted_betas[region][variable] = betas
                else:
                    predicted_betas[region] = {variable: betas, 'pred': predictors}

            thisqvals = qvals[basename]

            if 'adm0' in basename:
                calculation, dependencies, covarnames = country.prepare_csvv(filepath, thisqvals, betas_callback)
                ## XXX: Need to average to country-level
                columns = effectset.write_ncdf(thisqvals['weather'], targetdir, basename + suffix, weatherbundle, calculation, lambda region: (predgen1.get_current(region),), "Interpolated response for " + basename + ".", dependencies + weatherbundle.dependencies)
            elif 'adm2' in basename:
                ### XXX: Need to define subcountry
                calculation, dependencies, covarnames = subcountry.prepare_csvv(filepath, thisqvals, betas_callback)
                columns = effectset.write_ncdf(thisqvals['weather'], targetdir, basename + suffix, weatherbundle, calculation, lambda region: (predgen1.get_current(region),), "Interpolated response for " + basename + ".", dependencies + weatherbundle.dependencies)
            else:
                raise ValueError("Unknown calculation type: " + basename)

            with open(os.path.join(targetdir, basename + '-final.csv'), 'w') as fp:
                writer = csv.writer(fp)
                header = ['region'] + range(columns['sum'].shape[0])
                writer.writerow(header)
                for ii in range(len(weatherbundle.regions)):
                    row = [weatherbundle.regions[ii]] + list(columns['sum'][:, ii])
                    writer.writerow(row)

            with open(os.path.join(targetdir, basename + '-betas.csv'), 'w') as fp:
                writer = csv.writer(fp)

                header = ['region'] + covarnames[1:] + ['beta-temp']
                writer.writerow(header)

                for region in weatherbundle.regions:
                    if region not in predicted_betas:
                        row = [region] + ['NA'] * (len(header) - 1)
                    else:
                        row = [region] + [predicted_betas[region]['pred'][covar] for covar in covarnames[1:]] + [predicted_betas[region]['temp']]
                    writer.writerow(row)
