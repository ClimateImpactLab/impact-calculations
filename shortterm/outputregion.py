import csv, sys
import weather
from climate import forecasts, forecastreader

treader = forecastreader.MonthlyZScoreForecastReader(forecasts.temp_zscore_path, forecasts.temp_normstddev_path, 'ztemp', .5)
preader = forecastreader.MonthlyStochasticForecastReader(forecasts.prcp_path, 'prcp', .5)
prcp_climate_mean = list(forecasts.readncdf_allpred(forecasts.prcp_climate_path, 'mean', 0))

regions = weather.ForecastBundle(forecastreader.MonthlyForecastReader(forecasts.prcp_climate_path, 'mean')).regions

titer = treader.read_iterator()
piter = preader.read_iterator()

ii = regions.index(sys.argv[1])

with open('region-values.csv', 'w') as fp:
    writer = csv.writer(fp)
    writer.writerow(['time', 'temp', 'prcp', 'climprcp'])

    for time in treader.get_times():
        times1, temp = titer.next()
        times2, prcp = piter.next()

        assert times1 == times2

        writer.writerow([times1, temp[ii], prcp[ii], prcp_climate_mean[int(times1) % 12][ii]])
