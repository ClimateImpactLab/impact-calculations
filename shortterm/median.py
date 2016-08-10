import sys, os
import standard, weather, effectset
# from shortterm import standard, weather, effectset
from impacts import pvals

pvals = pvals.ConstantPvals(.5)

do_only = None

outputdir = sys.argv[1]
# outputdir = "tmp"

targetdir = os.path.join(outputdir, 'median', 'median')

weatherbundle = weather.FirstForecastBundle(weather.temp_path)

if os.path.exists(targetdir):
    continue

print targetdir
os.makedirs(targetdir)

pvals.make_pval_file(targetdir, pvals)
standard.produce(targetdir, weatherbundle, pvals, do_only=do_only)
