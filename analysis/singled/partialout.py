import sys, csv, os
sys.path.append("../../")

import numpy as np
from adaptation import csvvfile

csvvroot = "/shares/gcp/social/parameters/mortality/mortality_single_stage_12142016"
allbins = sys.argv[1]
allpreds = sys.argv[2]

covars = [None, 'meandays', 'log popop', 'log gdppc', 'age0-4', 'age65+']

savepreds = {} # {model => {region => {year => [preds]}}}

for pp in range(1, len(covars)):
    with open(allbins[:-4] + '-' + covars[pp].replace(' ', '') + '.csv', 'a') as outfp:
        writer = csv.writer(outfp)
        writer.writerow(['region', 'year', 'model', 'bin_nInfC_n17C', 'bin_n17C_n12C', 'bin_n12C_n7C', 'bin_n7C_n2C', 'bin_n2C_3C', 'bin_3C_8C', 'bin_8C_13C', 'bin_13C_18C', 'bin_23C_28C', 'bin_28C_33C', 'bin_33C_InfC'])

with open(allpreds, 'r') as predfp:
    predreader = csv.reader(predfp)
    predheader = predreader.next()

    for predrow in predreader:
        region = predrow[0]
        year = int(predrow[1])
        model = predrow[2]

        preds = map(float, predrow[3:])

        if model not in savepreds:
            savepreds[model] = {}
        if region not in savepreds[model]:
            savepreds[model][region] = {}
        savepreds[model][region][year] = preds

    predcols = predheader[3:]

with open(allbins, 'r') as binfp:
    binreader = csv.reader(binfp)
    binheader = binreader.next()

    current_model = None
    baselines = {} # region => [bins]

    for binrow in binreader:
        model = binrow[2]
        region = binrow[0]
        year = int(binrow[1])

        if model != current_model:
            print "New model:", model
            current_model = model
            baselines = {}

        if year == 1981:
            baselines[region] = map(float, binrow[4:])
            continue

        print year

        csvv = csvvfile.read(os.path.join(csvvroot, model + '.csvv'))
        partialsum = np.zeros(11)

        mybasepreds = savepreds[model][region][1981]
        myyearpreds = savepreds[model][region][year-1] # preds from previous year

        for pp in range(1, len(csvv['gamma']) / 11): # skip first
            with open(allbins[:-4] + '-' + covars[pp].replace(' ', '') + '.csv', 'a') as outfp:
                writer = csv.writer(outfp)

                gammas = csvv['gamma'][pp * 11 + np.arange(11)]
                if covars[pp] == 'meandays':
                    oldpreds = np.array([mybasepreds[predcols.index(col)] for col in ['meandays_nInfC_n17C', 'meandays_n17C_n12C', 'meandays_n12C_n7C', 'meandays_n7C_n2C', 'meandays_n2C_3C', 'meandays_3C_8C', 'meandays_8C_13C', 'meandays_13C_18C', 'meandays_23C_28C', 'meandays_28C_33C', 'meandays_33C_InfC']])
                    newpreds = np.array([myyearpreds[predcols.index(col)] for col in ['meandays_nInfC_n17C', 'meandays_n17C_n12C', 'meandays_n12C_n7C', 'meandays_n7C_n2C', 'meandays_n2C_3C', 'meandays_3C_8C', 'meandays_8C_13C', 'meandays_13C_18C', 'meandays_23C_28C', 'meandays_28C_33C', 'meandays_33C_InfC']])
                else:
                    oldpreds = float(mybasepreds[predcols.index(covars[pp])])
                    newpreds = float(myyearpreds[predcols.index(covars[pp])])

                partials = gammas * (newpreds - oldpreds)
                partialsum += partials

                writer.writerow(binrow[0:3] + list(np.array(filter(lambda v: not np.isnan(v), baselines[region])) + partials))

        # mismatches = np.logical_not(np.isclose(np.array(filter(lambda v: not np.isnan(v), baselines[region])) + partialsum, filter(lambda v: not np.isnan(v), map(float, binrow[4:]))))
        # recorded = np.array(filter(lambda v: not np.isnan(v), map(float, binrow[4:])))[mismatches]
        # assert len(recorded) == 0 or np.all(recorded[0] == recorded), str(np.array(filter(lambda v: not np.isnan(v), baselines[region])) + partialsum) + " <> " + str(filter(lambda v: not np.isnan(v), map(float, binrow[4:])))
        
