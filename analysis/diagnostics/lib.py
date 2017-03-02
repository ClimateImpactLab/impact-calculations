import subprocess

def show_julia(command):
    if isinstance(command, str):
        print command
        print "# " + subprocess.check_output(["julia", "-e", "println(" + command + ")"])
    else:
        print "\n".join(command)
        print "# " + subprocess.check_output(["julia", "-e", "; ".join(command[:-1]) + "; println(" + command[-1] + ")"])

def get_excerpt(filepath, first_col, regionid, years):
    data = {}
    with open(filepath, 'r') as fp:
        header = fp.readline().rstrip()
        data['header'] = header.split(',')[first_col:]
        print header
        print "..."
        for line in fp:
            if line[:len(regionid + ',XXXX')] in [regionid + ',' + str(year) for year in years]:
                print line.rstrip()
                print "..."
                data[line[len(regionid) + 1:len(regionid) + 5]] = map(float, line.split(',')[first_col:])

    return data

def excind(data, year, column):
    return data[str(year)][data['header'].index(column)]

def get_csvv(filepath):
    csvv = {}
    with open(filepath, 'r') as fp:
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

def show_coefficient(year, coefname, covartrans):
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
