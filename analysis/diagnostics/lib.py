import subprocess, csv

def show_header(text):
    print "\n\033[1m" + text + "\033[0m"

def show_julia(command):
    if isinstance(command, str):
        print command
        print "# " + subprocess.check_output(["julia", "-e", "println(" + command + ")"])
    else:
        print "\n".join(command)
        print "# " + subprocess.check_output(["julia", "-e", "; ".join(command[:-1]) + "; println(" + command[-1] + ")"])

def get_excerpt(filepath, first_col, regionid, years, hasmodel=True, onlymodel=None):
    data = {}
    model = None
    with open(filepath, 'r') as fp:
        for line in fp:
            if line.rstrip() == '...':
                break
        reader = csv.reader(fp)
        header = reader.next()
        data['header'] = header[first_col:]
        print ','.join(header)
        print "..."
        for row in reader:
            if '.' in row[1]:
                row[1] = str(int(float(row[1])))
            if row[0] == regionid and row[1] in map(str, years):
                if hasmodel:
                    if onlymodel is not None and row[2] != onlymodel:
                        continue
                    if model is None:
                        model = row[2]
                    elif model != row[2]:
                        break
                print ','.join(row)
                if int(row[1]) + 1 not in years:
                    print "..."
                data[row[1]] = map(float, row[first_col:])

    return data

def excind(data, year, column):
    return data[str(year)][data['header'].index(column)]

def get_csvv(filepath):
    csvv = {}
    with open(filepath, 'rU') as fp:
        printline = None
        for line in fp:
            if printline is not None:
                print line.rstrip()
                if printline == 'gamma':
                    csvv['gamma'] = map(float, line.rstrip().split(','))
                else:
                    csvv[printline] = map(lambda x: x.strip(), line.rstrip().split(','))
                printline = None
            if line.rstrip() in ["prednames", "covarnames", "gamma"]:
                printline = line.rstrip()

    return csvv

def show_coefficient(csvv, preds, year, coefname, covartrans):
    predyear = year - 1 if year > 2015 else year

    terms = []
    for ii in range(len(csvv['gamma'])):
        if csvv['prednames'][ii] == coefname:
            if csvv['covarnames'][ii] == '1':
                terms.append(str(csvv['gamma'][ii]))
            elif csvv['covarnames'][ii] in covartrans:
                terms.append(str(csvv['gamma'][ii]) + " * " + str(excind(preds, predyear, covartrans[csvv['covarnames'][ii]])))
            else:
                terms.append(str(csvv['gamma'][ii]) + " * " + str(excind(preds, predyear, csvv['covarnames'][ii])))

    show_julia(' + '.join(terms))

def show_coefficient_mle(csvv, preds, year, coefname, covartrans):
    predyear = year - 1 if year > 2015 else year

    terms = []
    for ii in range(len(csvv['gamma'])):
        if csvv['prednames'][ii] == coefname:
            if csvv['covarnames'][ii] in covartrans:
                terms.append(str(csvv['gamma'][ii]) + " * " + str(excind(preds, predyear, covartrans[csvv['covarnames'][ii]])))
            else:
                terms.append(str(csvv['gamma'][ii]) + " * " + str(excind(preds, predyear, csvv['covarnames'][ii])))

    beta = [csvv['gamma'][ii] if csvv['prednames'][ii] == coefname and csvv['covarnames'][ii] == '1' for ii in range(len(csvv['gamma']))][0]

    show_julia("%f * exp(%s)" % (beta, ' + '.join(terms)))

