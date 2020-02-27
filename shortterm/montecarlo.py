import sys, os, importlib
import allmodels, weather
from generate import pvalses

do_only = None
outputdir = sys.argv[1]

mod = importlib.import_module('impacts.conflict.allmodels')

for batch1 in range(100):
    for batch2 in range(100):
        targetdir = os.path.join(outputdir, 'batch' + str(batch1), 'batch' + str(batch2))
        if os.path.exists(targetdir):
            continue

        print(targetdir)
        os.makedirs(targetdir, 0o775)

        pvals = pvalses.OnDemandRandomPvals()

        weatherbundle = mod.get_bundle(pvals['weather'])

        mod.produce(targetdir, pvals)
        pvalses.make_pval_file(targetdir, pvals)
