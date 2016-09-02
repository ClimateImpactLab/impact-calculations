import sys, os
import standard, weather, effectset
from climate import forecasts, forecastreader
from impacts import pvalses

pvals = pvalses.ConstantPvals(.5)

do_only = None

outputdir = sys.argv[1]

targetdir = os.path.join(outputdir, 'median', 'median')

tbundle = weather.ForecastBundle(forecastreader.MonthlyZScoreForecastReader(forecasts.temp_zscore_path, forecasts.temp_normstddev_path, 'ztemp', .5))
pbundle = weather.ForecastBundle(forecastreader.MonthlyStochasticForecastReader(forecasts.prcp_path, 'prcp', .5))
weatherbundle = weather.CombinedBundle([tbundle, pbundle])

if os.path.exists(targetdir):
    os.system("rm -r " + targetdir)
    
print targetdir
os.makedirs(targetdir)

pvalses.make_pval_file(targetdir, pvals)
standard.produce(targetdir, weatherbundle, pvals, do_only=do_only)
