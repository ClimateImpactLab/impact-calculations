import sys, os
import standard, weather, effectset
from impacts.pvals import *

pvals = effectset.ConstantPvals(.5)

do_only = None

outputdir = sys.argv[1]

targetdir = os.path.join(outputdir, 'median', 'median')

if os.path.exists(targetdir):
    continue

print targetdir
os.makedirs(targetdir)

effectset.make_pval_file(targetdir, pvals)
standard.produce(targetdir, weatherbundle, get_model, pvals, do_only=do_only)
