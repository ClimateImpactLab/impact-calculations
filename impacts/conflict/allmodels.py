import glob, os, csv
from generate.weather import SingleWeatherBundle
from climate.dailyreader import DailyWeatherReader
from adaptation.econmodel import iterate_econmodels
from shortterm import weather, curvegen, effectset
from climate import forecasts, forecastreader
from adaptation import covariates
from . import standard

def get_bundle(qvals):
    source_temp_reader = forecastreader.MonthlyStochasticForecastReader(forecasts.temp_path, 'tas', qvals['tmean'])
    source_prcp_reader = forecastreader.MonthlyStochasticForecastReader(forecasts.prcp_path, 'prcp', qvals['pmean'])
    subcountry_temp_reader = forecastreader.CountryDeviationsReader(forecastreader.MonthlyZScoreForecastReader(source_temp_reader, forecasts.temp_mean_climate_path, forecasts.temp_sdev_climate_path, 'tas'))
    subcountry_prcp_reader = forecastreader.CountryDeviationsReader(source_prcp_reader)

    subcountry_tbundle = weather.ForecastBundle(subcountry_temp_reader)
    subcountry_pbundle = weather.ForecastBundle(subcountry_prcp_reader)

    country_temp_reader = forecastreader.CountryDuplicatedReader(forecastreader.MonthlyZScoreForecastReader(forecastreader.CountryAveragedReader(source_temp_reader), forecasts.temp_mean_climate_path, forecasts.temp_adm0sdev_climate_path, 'tas'), subcountry_tbundle.regions)
    country_prcp_reader = forecastreader.CountryDuplicatedReader(forecastreader.CountryAveragedReader(source_prcp_reader), subcountry_tbundle.regions)
    
    country_tbundle = weather.ForecastBundle(country_temp_reader)
    country_pbundle = weather.ForecastBundle(country_prcp_reader)

    # Note that defined in opposite order from above, because needed regions for country definition
    weatherbundle = weather.CombinedBundle([country_tbundle, country_pbundle, subcountry_tbundle, subcountry_pbundle])

    return weatherbundle

def produce(targetdir, weatherbundle, economicmodel, qvals, do_only=None, suffix=''):
    historicalbundle = SingleWeatherBundle(DailyWeatherReader("/shares/gcp/climate/BCSD/aggregation/cmip5/IR_level/historical/CCSM4/tas/tas_day_aggregated_historical_r1i1p1_CCSM4_%d.nc", 1991, 'SHAPENUM', 'tas'), 'historical', 'CCSM4')
    model, scenario, econmodel = next((mse for mse in iterate_econmodels() if mse[0] == 'high'))

    covariator = covariates.CombinedCovariator([covariates.TranslateCovariator(covariates.MeanWeatherCovariator(historicalbundle, 2015), {'climtas': 'tas'}),
                                                           covariates.EconomicCovariator(economicmodel, 2015, {'length': 1})])
    country_covariator = covariates.CountryAggregatedCovariator(covariator, weatherbundle.regions)
    subcountry_covariator = covariates.CountryDeviationCovariator(covariator, weatherbundle.regions)

    ## Full interpolation
    for filepath in glob.glob("/shares/gcp/social/parameters/conflict/hierarchical_08102017/*.csvv"):
        basename = os.path.basename(filepath)[:-5]
        print(basename)
        
        predicted_betas = {}
        def betas_callback(variable, region, predictors, betas):
            if region in predicted_betas:
                predicted_betas[region][variable] = betas
            else:
                predicted_betas[region] = {variable: betas, 'pred': predictors}

        thisqvals = qvals[basename]

        if 'adm0' in basename:
            calculation, dependencies, covarnames = standard.prepare_csvv(filepath, thisqvals, betas_callback, True)
            my_regions = configs.get_regions(weatherbundle.regions, lambda region: (country_covariator.get_current(region[:3]),))
            columns = effectset.write_ncdf(thisqvals['weather'], targetdir, basename + suffix, weatherbundle, calculation, my_regions, "Interpolated response for " + basename + ".", dependencies + weatherbundle.dependencies)
        elif 'adm2' in basename:
            calculation, dependencies, covarnames = standard.prepare_csvv(filepath, thisqvals, betas_callback, False)
            my_regions = configs.get_regions(weatherbundle.regions, lambda region: (subcountry_covariator.get_current(region),))
            columns = effectset.write_ncdf(thisqvals['weather'], targetdir, basename + suffix, weatherbundle, calculation, my_regions, "Interpolated response for " + basename + ".", dependencies + weatherbundle.dependencies)
        else:
            raise ValueError("Unknown calculation type: " + basename)

        with open(os.path.join(targetdir, basename + '-final.csv'), 'w') as fp:
            writer = csv.writer(fp)
            header = ['region'] + list(range(columns['sum'].shape[0]))
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
