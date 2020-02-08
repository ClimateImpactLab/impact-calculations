"""Functions to handle the data in old-style CSVV files.

These functions make old-style CSVV files expose the same fields as
new-style (Girdin) CSVVs. See csvvfile.py for more information.
"""

import csv, re
import numpy as np

def read(data, fp):
    """Interpret an old-style CSVV file into a dictionary of new-style information."""
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

    data['attrs']['csvv-version'] = 'legacy'
    data['gamma'] = np.array(data['gamma'][0])
    data['gammavcv'] = np.array(data['gammavcv'])
    data['residvcv'] = np.array(data['residvcv'])

    return data
