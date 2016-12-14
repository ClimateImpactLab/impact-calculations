import csv
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
            if len(row) == 0:
                continue
            if row[0] in ['NN', 'L', 'K']:
                data[row[0]] = int(row[1])
                if row[0] == 'K':
                    data['coefnames'] = row[2:]
                elif row[0] == 'L':
                    data['prednames'] = row[2:]
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
    data['gamma'] = multivariate_normal.rvs(data['gamma'], data['gannavcv'])
    data['gammavcv'] = None # this will cause errors if used again
    
def extract_values(data, kks, pattern=None):
    if pattern is None:
        print "WARNING: No pattern given to csvvfile.extract_values."
        
    indexes = []
    for kk in kks:
        indexes.extend(kk * data['L'] + np.arange(data['L']))
        if pattern is not None:
            for ll in range(data['L']):
                assert re.match(pattern.replace("{K}", str(kk)), prednames[kk * data['L'] + ll]) is not None
    indexes = np.array(indexes)

    gamma = data['gamma'][indexes]
    gammavcv = data['gammavcv'][indexes][:, indexes]
    if data['residvcv'].shape[0] > 0:
        residvcv = data['residvcv'][np.array(kks), np.array(kks)]
    else:
        residvcv = []

    return dict(gamma=gamma, gammavcv=gammavcv, residvcv=residvcv)

def by_predictor(csvv, params):
    gammas = []
    for ii in range(len(params) / csvv['L']):
        gammas.append(params[ii * csvv['L'] + np.arange(csvv['L'])])

    return gammas

if __name__ == '__main__':
    data = read("/shares/gcp/data/adaptation/conflict/group_tp3_bayes_auto.csv")

    print data
    print "Extracted [0]"
    print extract_values(data, [0])
