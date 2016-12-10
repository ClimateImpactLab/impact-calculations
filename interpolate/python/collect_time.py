import os, csv, re
import numpy as np
import reader, utils
from helpers import files
import helpers.header as headre
from openest.models.bin_model import BinModel

prednames = {}

filenames = ['brazil_decadal_coeffs.csv', 'IndiaDecadalCoefs.csv', 'ChinaDecadalCoefs.csv', 'USFinalResultsDecadal.csv', 'france_decadal_coeffs.csv', 'mexico_decadal_coeffs.csv']
groups = ['Brazil', 'India', 'China', 'USA', 'France', 'Mexico']

modelorder, allmodels, allpredictors, xx, hasnas = reader.collate_models(prednames, filenames, groups)

outdir = files.sharedpath('social/adaptation/predictors-time')
utils.clear_dir(outdir)

for jj in range(len(xx) - 1):
    if hasnas[jj]:
        continue

    with open(os.path.join(outdir, utils.bounds_to_string('bin', xx[jj], xx[jj+1]) + '.csv'), 'w') as fp:
        headre.write(fp, "NOT READY (based on preliminary input files)! Predictors for the temporal adaptation of the mortality bin from %.1f to %.1f" % (xx[jj], xx[jj+1]), # TODO: Remove NOT READY when input data has headers
                     headre.dated_version(utils.bounds_to_string('MORTALITY_TIME', xx[jj], xx[jj+1])),
                     filenames,
                     {'group': ('Group of spatial estimates (typically a country)', 'str'),
                      'year1': ('Starting year for estiamtion', 'year'),
                      'year2': ('Ending year for estiamtion', 'year'),
                      'coef': ('Estimated coefficient value', 'log mortality rate / day'),
                      'serr': ('Estimated coefficient standard error', 'log mortality rate / day')})

        writer = csv.writer(fp, quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
        writer.writerow(['group', 'year1', 'year2', 'coef', 'serr', 'avg_temp'])

        for fullname in modelorder:
            group = fullname.split('.')[0]
            member = fullname[len(group)+1:]
            years = re.split('_to_|to|-', member)
            assert len(years) == 2, "Row names must match the pattern YEAR_to_YEAR or YEAR-YEAR: " + member
            year1 = int(years[0])
            year2 = int(years[1])
            coef = allmodels[fullname].get_mean(index=jj)
            serr = allmodels[fullname].get_sdev(index=jj)

            writer.writerow([group, year1, year2, coef, serr])

