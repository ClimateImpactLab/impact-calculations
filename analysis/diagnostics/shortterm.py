import csv
import lib

def get_excerpt(filepath, regionid):
    with open(filepath, 'r') as fp:
        reader = csv.reader(fp)
        header = next(reader)
        print((','.join(header)))
        print("...")
        for row in reader:
            if row[0] == regionid:
                print((','.join(row)))
                return header[1:], list(map(float, row[1:]))

def show_coefficient(csvv, pred_header, preds, coefname, covartrans):
    terms = []
    for ii in range(len(csvv['gamma'])):
        if csvv['prednames'][ii] == coefname:
            if csvv['covarnames'][ii] == '1':
                terms.append(str(csvv['gamma'][ii]))
            elif csvv['covarnames'][ii] in covartrans:
                terms.append(str(csvv['gamma'][ii]) + " * " + str(preds[pred_header.index(covartrans[csvv['covarnames'][ii]])]))
            else:
                terms.append(str(csvv['gamma'][ii]) + " * " + str(preds[pred_header.index(csvv['covarnames'][ii])]))

    lib.show_julia(' + '.join(terms))

