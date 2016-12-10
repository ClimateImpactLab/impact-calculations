import os, csv
import numpy as np
import reader, utils
from helpers import files
import helpers.header as headre
from impacts import caller
from openest.models.bin_model import BinModel

#prednames = {'avg_temp': ['avg_temp', 'avg_tempC'], 'gdppc': ['gdppc']}
prednames = {'avg_temp': ['avg_temp', 'avg_tempC'], 'gdppc': ['gdppc'], 'meandays_nInfC_n17C': ['meandays_nInfC_n17C', 'meandays_nInf_n17C'], 'meandays_n17C_n12C': ['meandays_n17C_n12C'], 'meandays_n12C_n7C': ['meandays_n12C_n7C'], 'meandays_n7C_n2C': ['meandays_n7C_n2C'], 'meandays_n2C_3C': ['meandays_n2C_3C'], 'meandays_3C_8C': ['meandays_3C_8C'], 'meandays_8C_13C': ['meandays_8C_13C'], 'meandays_13C_18C': ['meandays_13C_18C'], 'meandays_23C_28C': ['meandays_23C_28C'], 'meandays_28C_33C': ['meandays_28C_33C'], 'meandays_33C_InfC': ['meandays_33C_InfC', 'meandays_33C_Inf'], 'popop': ['popop']}
ignores = ['meandays_18C_23C', '_merge', 'avg_temp', 'avg_tempC', 'region_str']

for group in ['all', '65+']:
    if group == 'all':
        filenames = ['inputs-apr-7/BRA_adm1.csv', 'inputs-apr-7/IND_adm1.csv', 'inputs-apr-7/CHN_adm1.csv', 'inputs-apr-7/USA_adm1.csv', 'inputs-apr-7/FRA_adm1.csv', 'inputs-apr-7/MEX_adm1.csv']
        groups = ['Brazil', 'India', 'China', 'USA', 'France', 'Mexico']
        additionals = [{'gcpid': 'GHA2003_BRA_national_mortality_all',
                       'model': caller.get_model_by_gcpid('GHA2003_BRA_national_mortality_all'),
                       'gdppc': 4364., 'avg_temp': 21.25, 'group': 'Brazil2', 'popop': 11970.},
                      {'gcpid': 'VSMPMCL2004_FRA_national_mortality_all',
                       'model': caller.get_model_by_gcpid('VSMPMCL2004_FRA_national_mortality_all'),
                       'gdppc': 25494.29, 'avg_temp': 19., 'group': 'France2', 'popop': 9809.}]
    else:
        filenames = ['inputs-apr-7/BRA_adm1_65+.csv', 'inputs-apr-7/MEX_adm1_65+.csv', 'inputs-apr-7/USA_adm1_65+.csv', 'inputs-apr-7/FRA_adm1_65+.csv']
        groups = ['Brazil', 'Mexico', 'USA', 'France']
        additionals = [{'gcpid': 'GHA2003_BRA_national_mortality_65plus',
                       'model': caller.get_model_by_gcpid('GHA2003_BRA_national_mortality_65plus'),
                       'gdppc': 4364., 'avg_temp': 21.25, 'group': 'Brazil2', 'popop': 11970.}]

    # Add day bin data from file
    with open(files.sharedpath("social/adaptation/day_bins.csv"), 'r') as fp:
        csvreader = csv.reader(fp)
        headrow = csvreader.next()
        for row in csvreader:
            # Find matching additionals
            for additional in additionals:
                if additional['gcpid'][:len(row[0])] == row[0]:
                    for cc in range(1, len(row)):
                        additional[headrow[cc]] = row[cc]

    dependencies = []
    modelorder, allmodels, allpredictors, xx, allnas = reader.collate_models(prednames, ignores, filenames, groups, additionals, dependencies)

    outdir = files.datapath('adaptation/predictors-space-' + group)
    utils.clear_dir(outdir)

    for jj in range(len(xx) - 1):
        if allnas[jj]:
            continue

        with open(os.path.join(outdir, utils.bounds_to_string('bin', xx[jj], xx[jj+1]) + '.csv'), 'w') as fp:
            headre.write(fp, "Predictors for the spatial interpolation of the mortality bin from %.1f to %.1f" % (xx[jj], xx[jj+1]),
                         headre.dated_version(utils.bounds_to_string('MORTALITY_SPACE', xx[jj], xx[jj+1])),
                         filenames,
                         {'group': ('Group of spatial estimates (typically a country)', 'str'),
                          'member': ('Member within the group (typically a ADM 1 region)', 'str'),
                          'coef': ('Estimated coefficient value', 'log mortality rate / day'),
                          'serr': ('Estimated coefficient standard error', 'log mortality rate / day'),
                          'avg_temp': ('Average temperature', 'deg. C'),
                          'gdppc': ('GDP per capita', '$ 2005 PPP'),
                          'meandays_*': ('Average number of days in bin per year', 'days')
                         })

            writer = csv.writer(fp, quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
            predcols = ['avg_temp', 'gdppc', 'meandays_nInfC_n17C', 'meandays_n17C_n12C', 'meandays_n12C_n7C', 'meandays_n7C_n2C', 'meandays_n2C_3C', 'meandays_3C_8C', 'meandays_8C_13C', 'meandays_13C_18C', 'meandays_23C_28C', 'meandays_28C_33C', 'meandays_33C_InfC', 'popop']
            writer.writerow(['group', 'member', 'coef', 'serr'] + predcols)

            for fullname in modelorder:
                group = fullname.split('.')[0]
                member = fullname[len(group)+1:]
                coef = allmodels[fullname].get_mean(index=jj)
                serr = allmodels[fullname].get_sdev(index=jj)
                predvals = [allpredictors[fullname][predcol] for predcol in predcols]

                writer.writerow([group, member, coef, serr] + predvals)

