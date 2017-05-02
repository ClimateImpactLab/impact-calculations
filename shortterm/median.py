import sys, os, importlib
import weather
from generate import pvalses

do_only = None
outputdir = sys.argv[1]

mod = importlib.import_module('impacts.conflict.allmodels')

pvals = pvalses.ConstantPvals(.5)

targetdir = os.path.join(outputdir, 'median', 'median')

if os.path.exists(targetdir):
    os.system("rm -r " + targetdir)

print targetdir
os.makedirs(targetdir)

weatherbundle = mod.get_bundle(pvals['weather'])

mod.produce(targetdir, weatherbundle, pvals)
pvalses.make_pval_file(targetdir, pvals)
