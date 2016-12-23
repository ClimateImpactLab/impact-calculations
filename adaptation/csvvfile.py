import csv, re
import numpy as np
import metacsv
from scipy.stats import multivariate_normal

def read(filename):
    with open(filename, 'r') as fp:
        attrs, variables, coords = metacsv.read_header(fp)
        data = {'attrs': attrs, 'variables': variables, 'coords': coords}

        reader = csv.reader(fp)
        lastappend = None
        for row in reader:
            if len(row) == 0 or (len(row) == 1 and len(row[0].strip()) == 0):
                continue
            if row[0] in ['NN', 'L', 'K']:
                data[row[0]] = int(row[1])
                if row[0] == 'K':
                    data['coefnames'] = map(lambda s: s.strip(), row[2:])
                elif row[0] == 'L':
                    data['prednames'] = map(lambda s: s.strip(), row[2:])
            elif row[0] in ['gamma', 'gammavcv', 'residvcv']:
                data[row[0]] = []
                lastappend = row[0]
            else:
                if lastappend is None:
                    print "Expected lastappend to be available."
                    print row
                assert lastappend is not None
                data[lastappend].append(map(float, row))

        data['gamma'] = np.array(data['gamma'][0])
        data['gammavcv'] = np.array(data['gammavcv'])
        data['residvcv'] = np.array(data['residvcv'])

        return data

def collapse_bang(data, seed):
    if seed == None:
        data['gammavcv'] = None
    else:
        data['gamma'] = multivariate_normal.rvs(data['gamma'], data['gammavcv'])
        data['gammavcv'] = None # this will cause errors if used again

def extract_values(data, kks, pattern=None, lorder=False):
    if pattern is None:
        print "WARNING: No pattern given to csvvfile.extract_values."

    indexes = []
    for kk in kks:
        if not lorder:
            indexes.extend(kk * data['L'] + np.arange(data['L']))
            if pattern is not None:
                for ll in range(data['L']):
                    assert re.match(pattern.replace("{K}", str(kk)), data['prednames'][kk * data['L'] + ll]) is not None, pattern.replace("{K}", str(kk)) + " does not match " + data['prednames'][kk * data['L'] + ll]
        else:
            indexes.extend(kk + data['K'] * np.arange(data['L']))
            if pattern is not None:
                for ll in range(data['L']):
                    assert re.match(pattern.replace("{K}", str(kk)), data['prednames'][kk + data['K'] * ll]) is not None, pattern.replace("{K}", str(kk)) + " does not match " + data['prednames'][kk + data['K'] * ll]

    indexes = np.array(indexes)

    gamma = data['gamma'][indexes]
    gammavcv = data['gammavcv'][indexes][:, indexes]
    if data['residvcv'].shape[0] > 0:
        residvcv = data['residvcv'][np.array(kks), np.array(kks)]
    else:
        residvcv = []

    return dict(gamma=gamma, gammavcv=gammavcv, residvcv=residvcv)

def by_predictor_lk(csvv, params, setsize):
    gammas = []
    names = []
    for ii in range(len(params) / setsize):
        gammas.append(params[ii * setsize + np.arange(setsize)])
        namesrow = []
        for jj in np.arange(setsize):
            namesrow.append(csvv['prednames'][ii * setsize + jj])
        names.append(namesrow)

    print names
    return gammas

def by_predictor_kl(csvv, params, setsize):
    gammas = []
    names = []
    for ii in range(len(params) / setsize):
        gammas.append(params[ii + (len(params) / setsize) * np.arange(setsize)])
        namesrow = []
        for jj in np.arange(setsize):
            namesrow.append(csvv['prednames'][ii + (len(params) / setsize) * jj])
        names.append(namesrow)

    print names
    return gammas

if __name__ == '__main__':
    data = read("/shares/gcp/data/adaptation/conflict/group_tp3_bayes_auto.csv")

    print data
    print "Extracted [0]"
    print extract_values(data, [0])
