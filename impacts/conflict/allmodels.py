import glob, os, csv
from generate.weather import SingleWeatherBundle
from climate.dailyreader import DailyWeatherReader
from adaptation.econmodel import iterate_econmodels
from shortterm import weather, curvegen, effectset
from climate import forecasts, forecastreader
import standard

def get_bundle(qvals):
    subcountry_tbundle = weather.ForecastBundle(forecastreader.CountryDeviationsReader(forecastreader.MonthlyZScoreForecastOTFReader(forecasts.temp_path, forecasts.temp_climate_path, 'mean', qvals['tmean'])))
    subcountry_pbundle = weather.ForecastBundle(forecastreader.CountryDeviationsReader(forecastreader.MonthlyStochasticForecastReader(forecasts.prcp_path, 'prcp', qvals['pmean'])))
    country_tbundle = weather.ForecastBundle(forecastreader.CountryDuplicatedReader(forecastreader.CountryAveragedReader(forecastreader.MonthlyZScoreForecastReader(forecasts.temp_path)), subcountry_tbundle.regions))
    country_pbundle = weather.ForecastBundle(forecastreader.CountryDuplicatedReader(forecastreader.CountryAveragedReader(forecastreader.MonthlyStochasticForecastReader(forecasts.prcp_path, 'prcp', qvals['pmean'])), subcountry_tbundle.regions))

    # Note that defined in opposite order from above, because need regions
    weatherbundle = weather.CombinedBundle([country_tbundle, country_pbundle, subcountry_tbundle, subcountry_pbundle])

    return weatherbundle

def produce(targetdir, weatherbundle, qvals, do_only=None, suffix=''):
    historicalbundle = SingleWeatherBundle(DailyWeatherReader("/shares/gcp/climate/BCSD/aggregation/cmip5/IR_level/historical/CCSM4/tas/tas_day_aggregated_historical_r1i1p1_CCSM4_%d.nc", 1991, 'SHAPENUM', 'tas'), 'historical', 'CCSM4')
    model, scenario, econmodel = (mse for mse in iterate_econmodels() if mse[0] == 'high').next()

    covariator = covariates.CombinedCovariator([covariates.TranslateCovariator(covariates.MeanWeatherCovariator(historicalbundle, 30, 2015), {'climtas': 'tas'}),
                                                           covariates.EconomicCovariator(economicmodel, 13, 2015)])
    country_covariator = covariates.CountryAggregatedCovariator(covariator, weatherbundle.regions)
    subcountry_covariator = covariates.CountryDeviationCovariator(covariator, weatherbundle.regions)

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
            calculation, dependencies, covarnames = standard.prepare_csvv(filepath, thisqvals, betas_callback, tp_index0=0)
            columns = effectset.write_ncdf(thisqvals['weather'], targetdir, basename + suffix, weatherbundle, calculation, lambda region: (country_covariator.get_current(region),), "Interpolated response for " + basename + ".", dependencies + weatherbundle.dependencies)
        elif 'adm2' in basename:
            calculation, dependencies, covarnames = standard.prepare_csvv(filepath, thisqvals, betas_callback, tp_index0=2)
            columns = effectset.write_ncdf(thisqvals['weather'], targetdir, basename + suffix, weatherbundle, calculation, lambda region: (subcountry_covariator.get_current(region),), "Interpolated response for " + basename + ".", dependencies + weatherbundle.dependencies)
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
