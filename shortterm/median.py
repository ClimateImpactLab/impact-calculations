import sys, os, importlib
from . import weather
from adaptation import econmodel
from generate import pvalses

do_only = None
outputdir = sys.argv[1]

mod = importlib.import_module('impacts.conflict.allmodels')

pvals = pvalses.ConstantPvals(.5)

targetdir = os.path.join(outputdir, 'median', 'median')

if os.path.exists(targetdir):
    os.system("rm -r " + targetdir)

print(targetdir)
os.makedirs(targetdir, 0o775)

weatherbundle = mod.get_bundle(pvals['weather'])
economicmodel = econmodel.get_economicmodel('SSP2', 'low')

mod.produce(targetdir, weatherbundle, economicmodel, pvals)
pvalses.make_pval_file(targetdir, pvals)
