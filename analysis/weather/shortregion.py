import numpy as np
from climate import forecasts, forecastreader
from shortterm import weather

tbundle = weather.ForecastBundle(forecastreader.MonthlyZScoreForecastReader(forecasts.temp_zscore_path, forecasts.temp_normstddev_path, 'ztemp', .5))
pbundle = weather.ForecastBundle(forecastreader.MonthlyStochasticForecastReader(forecasts.prcp_path, 'prcp', .5))
weatherbundle = weather.CombinedBundle([tbundle, pbundle])

prcp_climate_mean = list(forecasts.readncdf_allpred(forecasts.prcp_climate_path, 'mean', 0))
regions = weather.ForecastBundle(forecastreader.MonthlyForecastReader(forecasts.prcp_climate_path, 'mean')).regions

region = "IRQ.10.55"

rr = weatherbundle.regions.index(region)
for month, values in weatherbundle.monthbundles(.5):
    assert regions[rr] == region
    print month, values[0][rr], values[1][rr], prcp_climate_mean[int(month) % 12][rr]
