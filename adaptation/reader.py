import csv
import numpy as np
from helpers import files
import helpers.header as headre
import utils
try:
    from openest.models.bin_model import BinModel
    from openest.models.spline_model import SplineModel
except:
    print "Cannot load open-estimate; conversion to models will fail."

def csv_to_data(filename, prednames, ignores, dependencies, predcheck={}):
    # Headers separate
    headerfilename = filename.replace('.csv', '.fgh').replace('_65+', '').replace('_jr', '').replace('_alternate', '')
    with open(headerfilename, 'r') as fp:
        headre.deparse(fp, dependencies)

    possibleprednames = []
    for predname in prednames:
        for colname in prednames[predname]:
            possibleprednames.append(colname)

    with open(filename, 'r') as fp:
        reader = csv.reader(fp)
        header = reader.next()

        omitted_column = header.index('omitted_bin')

        # Check that we have coefbin_...'s followed by stderrbin_...'s
        coefstart = omitted_column + 1
        if header[coefstart] == 'coef_cons' and header[coefstart+1] == 'stderr_cons':
            coefstart += 2
        if header[coefstart] in ignores:
            coefstart += 1
        serrend = len(header)
        while header[serrend - 1] in ['coeftrend', 'stderrtrend'] or header[serrend - 1] in possibleprednames or header[serrend - 1] in ignores:
            serrend -= 1
        serrstart = (serrend - coefstart) / 2 + coefstart
        binlos = []
        binhis = []
        for ii in range(serrstart - coefstart):
            coefs = utils.string_to_bounds(header[coefstart + ii])
            serrs = utils.string_to_bounds(header[serrstart + ii])

            assert coefs[0] in ['coefbin', 'bin'], "Column " + str(coefstart + ii + 1) + " is not recognized as a coeff."
            assert serrs[0] in ['stderrbin', 'se'], "Column " + str(serrstart + ii + 1) + " is not recognized as a std. err."
            assert coefs[1] == serrs[1], "Column " + str(coefstart + ii + 1) + " and " + str(serrstart + ii + 1) + " do not have matching lower bounds: " + str(coefs[1]) + " vs. " + str(serrs[1])
            assert coefs[2] == serrs[2], "Column " + str(coefstart + ii + 1) + " and " + str(serrstart + ii + 1) + " do not have matching upper bounds."

            binlos.append(coefs[1])
            binhis.append(coefs[2])

        omitlo = None
        omithi = None
        regions_done = set()
        for row in reader:
            if not row:
                continue
            assert row[0] not in regions_done, "The same region is represented twice."
            if row[omitted_column] == '':
                print "Skipping row " + row[0]
                continue

            coefs = []
            serrs = []
            for ii in range(serrstart - coefstart):
                coefs.append(float(row[coefstart + ii]) if row[coefstart + ii] else np.nan)
                serr = float(row[serrstart + ii]) if row[serrstart + ii] else np.inf
                if serr == 0:
                    serr = np.inf
                serrs.append(serr)

            omitted = row[omitted_column].split('_to_')
            if len(omitted) == 1:
                omitted = row[omitted_column].split('-')
            assert omitted[0][-1] in ['C', 'F'], "Omitted bin must be in C or F"
            if omitted[0][-1] == 'C':
                myomitlo = float(omitted[0][:-1])
            else:
                myomitlo = (float(omitted[0][:-1]) - 32) / 1.8
            if omitlo is None:
                omitlo = myomitlo
            else:
                assert omitlo == myomitlo, "Lower bound of omitted bin changed."
            assert omitted[1][-1] in ['C', 'F'], "Omitted bin must be in C or F"
            if omitted[1][-1] == 'C':
                myomithi = float(omitted[1][:-1])
            else:
                myomithi = (float(omitted[1][:-1]) - 32) / 1.8
            if omithi is None:
                omithi = myomithi
            else:
                assert omithi == myomithi, "Upper bound of omitted bin changed."

            mybinlos = np.array(binlos + [omitlo])
            mybinhis = np.array(binhis + [omithi])
            coefs.append(np.nan)
            serrs.append(np.nan)

            order = np.argsort(mybinlos)
            assert np.allclose(mybinlos[order[1:]], mybinhis[order[:-1]]), "Upper and lower bounds don't line up."

            predictors = {}
            for predname in prednames:
                foundname = None
                for colname in prednames[predname]:
                    if colname in header:
                        foundname = colname

                assert foundname is not None, "Predictor " + predname + " not found."
                predictors[predname] = float(row[header.index(foundname)])
                if predname in predcheck:
                    predcheck[predname](predictors[predname])

            regions_done.add(row[0])
            yield row[0], mybinlos.tolist(), mybinhis.tolist(), coefs, serrs, predictors

def csv_to_models(filename, prednames, ignores, dependencies):
    shown = False
    for name, binlos, binhis, coefs, serrs, predictors in csv_to_data(filename, prednames, ignores, dependencies):
        mybinlos = np.array(binlos)
        mybinhis = np.array(binhis)

        order = np.argsort(mybinlos)

        gausmodel = SplineModel.create_gaussian({ii: (coefs[order[ii]], serrs[order[ii]] ** 2) for ii in range(len(order))})
        model = BinModel(mybinlos[order].tolist() + [mybinhis[order[-1]]], gausmodel)

        yield name, model, predictors

def collate_models(prednames, ignores, filenames, groups, additionals, dependencies):
    modelorder = []
    allmodels = {}
    allpredictors = {}
    for ii in range(len(filenames)):
        print filenames[ii]
        for name, model, predictors in csv_to_models(files.datapath('adaptation/' + filenames[ii]), prednames, ignores, dependencies):
            fullname = groups[ii] + "." + name
            modelorder.append(fullname)
            allmodels[fullname] = model
            allpredictors[fullname] = predictors

    # Include other models as given
    for additional in additionals:
        fullname = additional['group'] + '.' + additional['gcpid']
        modelorder.append(fullname)
        allmodels[fullname] = additional['model']
        allpredictors[fullname] = {key: additional[key] for key in additional if key not in ['group', 'gcpid', 'model']}

    # Make bins all consistent
    # Also check that same bins are missing
    newmodels = BinModel.consistent_bins(allmodels.values())
    xx = newmodels[0].get_xx()

    allnas = [True] * (len(xx) - 1)
    for ii in range(len(newmodels)):
        allmodels[allmodels.keys()[ii]] = newmodels[ii]
        for jj in range(len(xx) - 1):
            serr = newmodels[ii].get_sdev(index=jj)
            if not np.isnan(serr) and serr > 0:
                allnas[jj] = False

    return modelorder, allmodels, allpredictors, xx, allnas

if __name__ == '__main__':
    import os, sys

    path = sys.argv[1]

    prednames = {'avg_temp': ['avg_temp', 'avg_tempC'], 'gdppc': ['gdppc'], 'meandays_nInfC_n17C': ['meandays_nInfC_n17C', 'meandays_nInf_n17C'], 'meandays_n17C_n12C': ['meandays_n17C_n12C'], 'meandays_n12C_n7C': ['meandays_n12C_n7C'], 'meandays_n7C_n2C': ['meandays_n7C_n2C'], 'meandays_n2C_3C': ['meandays_n2C_3C'], 'meandays_3C_8C': ['meandays_3C_8C'], 'meandays_8C_13C': ['meandays_8C_13C'], 'meandays_13C_18C': ['meandays_13C_18C'], 'meandays_23C_28C': ['meandays_23C_28C'], 'meandays_28C_33C': ['meandays_28C_33C'], 'meandays_33C_InfC': ['meandays_33C_InfC', 'meandays_33C_Inf']}
    ignores = ['meandays_18C_23C', '_merge', 'region_str']

    def check_avg_C(v):
        assert v < 40, "Interpretted as C, avg. temp of " + str(v) + " too high!"
    def check_gdppc(v):
        assert v > 0, "GDP per capita needs to be greater than 0."
    predcheck = {'avg_temp': check_avg_C, 'gdppc': check_gdppc}

    dependencies = []

    if os.path.isfile(path):
        try:
            for name, binlos, binhis, coefs, serrs, predictors in csv_to_data(path, prednames, ignores, dependencies, predcheck):
                pass
        except Exception as ex:
            print path, "error:", ex
    else:
        for filename in os.listdir(path):
            if not os.path.isfile(path + filename) or filename[-4:] != '.csv':
                continue
            try:
                for name, binlos, binhis, coefs, serrs, predictors in csv_to_data(path + filename, prednames, ignores, dependencies, predcheck):
                    pass
            except Exception as ex:
                print filename, "error:", ex


