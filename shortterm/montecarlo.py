import sys, os
import standard, weather, pvalses
from climate import forecasts, forecastreader
from impacts import pvalses

do_only = None
outputdir = sys.argv[1]

for batch in range(10000):
    targetdir = os.path.join(outputdir, 'sxsw', 'batch' + str(batch), )
    if os.path.exists(targetdir):
        continue

    print targetdir
    os.makedirs(targetdir)

    pvals = pvalses.OnDemandRandomPvals()

    tbundle = weather.ForecastBundle(forecastreader.MonthlyZScoreForecastReader(forecasts.temp_zscore_path, forecasts.temp_normstddev_path, 'ztemp', pvals['weather']['ztemp']))
    pbundle = weather.ForecastBundle(forecastreader.MonthlyStochasticForecastReader(forecasts.prcp_path, 'prcp', pvals['weather']['prcp']))
    weatherbundle = weather.CombinedBundle([tbundle, pbundle])

    standard.produce(targetdir, weatherbundle, pvals, do_only=do_only)
    pvalses.make_pval_file(targetdir, pvals)
