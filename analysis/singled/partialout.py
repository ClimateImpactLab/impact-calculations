import sys, csv
from adaptation import csvvfile

csvvroot = "/shares/gcp/social/parameters/mortality/mortality_single_stage_12142016"
allbins = sys.argv[1]
allpreds = sys.argv[1]

covars = [None, 'meandays', 'log popop', 'log gdppc', 'age0-4', 'age65+']

with open(allbins, 'r') as binfp:
    binreader = csv.reader(binfp)
    binheader = binreader.next()

    with open(allpreds, 'r') as predfp:
        predreader = csv.reader(predfp)
        predheader = predreader.next()

        current_model = None
        baselines = {} # region => [bins]
        basepreds = {} # region => [preds]

        for binrow in binheader.next():
            predrow = predheader.next()
            assert binrow[0:3] == predrow[0:3]

            if binrow[2] != current_model:
                print "New model:", binrow[2]
                baselines = {}

            if binrow[1] == '1981':
                baselines[binrow[0]] = map(float, binrow[4:])
                basepreds[binrow[0]] = predrow

            csvv = csvvfile.read(os.path.join(csvvroot, binrow[2] + '.csvv'))
            partialsum = zeros(11)

            mybasepreds = basepreds[binrow[0]]

            for pp in range(1, len(csvv['gammas']) / 11): # skip first
                with open(allbins[-4:] + '-' + str(pp) + '.csv', 'a') as outfp:
                    writer = writer.csv(outfp)

                    gammas = csvv['gammas'][pp * 11 + np.arange(11)]
                    if covars[pp] == 'meandays':
                        oldpreds = np.array([float(mybasepreds[predheader.index(col)]) for col in ['meandays_nInfC_n17C', 'meandays_n17C_n12C', 'meandays_n12C_n7C', 'meandays_n7C_n2C', 'meandays_n2C_3C', 'meandays_3C_8C', 'meandays_8C_13C', 'meandays_13C_18C', 'meandays_18C_23C', 'meandays_23C_28C', 'meandays_28C_33C', 'meandays_33C_InfC']])
                        newpreds = np.array([float(predrow[predheader.index(col)]) for col in ['meandays_nInfC_n17C', 'meandays_n17C_n12C', 'meandays_n12C_n7C', 'meandays_n7C_n2C', 'meandays_n2C_3C', 'meandays_3C_8C', 'meandays_8C_13C', 'meandays_13C_18C', 'meandays_18C_23C', 'meandays_23C_28C', 'meandays_28C_33C', 'meandays_33C_InfC']])
                    else:
                        oldpreds = float(mybasepreds[predheader.index(covars[pp])])
                        newpreds = float(predrow[predheader.index(covars[pp])])

                    partials = gammas * (newpreds - oldpreds)
                    partialsum += partials

                    writer.writerow(binrow[0:3] + list(baselines[binrow[0]] + partials))

            assert baselines[binrow[0]] + partialsum == map(float, binrow[4:])
