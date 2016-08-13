import sys, os
import standard, weather, effectset
from impacts import pvalses

pvals = pvalses.ConstantPvals(.5)

do_only = None

outputdir = sys.argv[1]

targetdir = os.path.join(outputdir, 'median', 'median')

tbundle = weather.FirstForecastBundle(weather.temp_path)
pbundle = weather.FirstForecastBundle(weather.prcp_path)
weatherbundle = weather.CombinedBundle([tbundle, pbundle])

if os.path.exists(targetdir):
    os.system("rm -r " + targetdir)
    
print targetdir
os.makedirs(targetdir)

pvalses.make_pval_file(targetdir, pvals)
standard.produce(targetdir, weatherbundle, pvals, do_only=do_only)
