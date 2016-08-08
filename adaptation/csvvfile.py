import csv
import numpy as np
import metacsv

def read(filename):
    with open(filename, 'r') as fp:
        attrs, variables, coords = metacsv.read_header(fp)
        data = {'attrs': attrs, 'variables': variables, 'coords': coords}

        reader = csv.reader(fp)
        lastappend = None
        for row in reader:
            if row[0] in ['NN', 'L', 'K']:
                data[row[0]] = float(row[1])
                if row[0] == 'K':
                    data['coefnames'] = row[2:]
                elif row[0] == 'L':
                    data['prednames'] = row[2:]
            elif row[0] in ['gamma', 'gammavcv', 'residvcv']:
                data[row[0]] = []
                lastappend = row[0]
            else:
                assert lastappend is not None
                data[lastappend].append(map(float, row))

        data['gamma'] = np.array(data['gamma'])
        data['gammavcv'] = np.array(data['gammavcv'])
        data['residvcv'] = np.array(data['residvcv'])

        return data

if __name__ == '__main__':
    print read("/shares/gcp/data/adaptation/conflict/group_tp3_bayes_auto.csv")
