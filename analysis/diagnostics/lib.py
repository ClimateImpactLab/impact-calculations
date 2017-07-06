import subprocess, csv
import numpy as np
from netCDF4 import Dataset

def show_header(text):
    print "\n\033[1m" + text + "\033[0m"

def show_julia(command, clipto=160):
    if isinstance(command, str):
        print command
        print "# " + subprocess.check_output(["julia", "-e", "println(" + command + ")"])
    else:
        for line in command:
            if clipto is not None and len(line) > clipto:
                print line[:(clipto-3)] + '...'
            else:
                print line
                
        print "# " + subprocess.check_output(["julia", "-e", "; ".join(command[:-1]) + "; println(" + command[-1] + ")"])

def get_excerpt(filepath, first_col, regionid, years, hasmodel=True, onlymodel=None, hidecols=[]):
    data = {}
    model = None
    with open(filepath, 'r') as fp:
        for line in fp:
            if line.rstrip() == '...':
                break
        reader = csv.reader(fp)
        header = reader.next()
        data['header'] = header[first_col:]
        # Find columns to hide
        showcols = np.array([col not in hidecols for col in header])
        
        print ','.join(np.array(header)[showcols])
        print "..."
        for row in reader:
            if 'e+06' in row[1]:
                row[1] = str(int(float(row[1]) / 1000))
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
                print ','.join(np.array(row)[showcols[:len(row)]])
                if int(row[1]) + 1 not in years:
                    print "..."
                if row[1] in data:
                    # Just fill in NAs (until we figure out why dubling up lines)
                    for ii in range(len(data[row[1]])):
                        if np.isnan(data[row[1]][ii]):
                            data[row[1]][ii] = float(row[first_col+ii])
                else:
                    data[row[1]] = map(lambda x: float(x) if x != 'NA' else np.nan, row[first_col:])

    return data

def excind(data, year, column):
    return data[str(year)][data['header'].index(column)]

def get_csvv(filepath, index0=None, indexend=None):
    csvv = {}
    with open(filepath, 'rU') as fp:
        printline = None
        for line in fp:
            if printline is not None:
                if printline == 'gamma':
                    csvv['gamma'] = map(float, line.rstrip().split(','))
                else:
                    csvv[printline] = map(lambda x: x.strip(), line.rstrip().split(','))

                if index0 is not None:
                    csvv[printline] = csvv[printline][index0:indexend]
                print ','.join(map(str, csvv[printline]))
                    
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
            if csvv['covarnames'][ii] == '1':
                continue
            elif csvv['covarnames'][ii] in covartrans:
                terms.append(str(csvv['gamma'][ii]) + " * " + str(excind(preds, predyear, covartrans[csvv['covarnames'][ii]])))
            else:
                terms.append(str(csvv['gamma'][ii]) + " * " + str(excind(preds, predyear, csvv['covarnames'][ii])))

    beta = [csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['prednames'][ii] == coefname and csvv['covarnames'][ii] == '1'][0]

    show_julia("%f * exp(%s)" % (beta, ' + '.join(terms)))

def get_regionindex(region):
    with open("/shares/gcp/regions/hierarchy.csv", 'r') as fp:
        for line in fp:
            if line[0] != '#':
                break

        reader = csv.reader(fp)
        for row in reader:
            if row[0] == region:
                return int(row[6]) - 1

def get_weather(weathertemplate, years, shapenum, show_all_years=[]):
    weather = {}
    for year in years:
        rootgrp = Dataset(weathertemplate.format('historical' if year < 2006 else 'rcp85', year), 'r', format='NETCDF4')
        data = rootgrp.variables['tas'][:, shapenum]
        rootgrp.close()

        if year in show_all_years:
            print str(year) + ': ' + ','.join(map(str, data))
        else:
            print str(year) + ': ' + ','.join(map(str, data[:10])) + '...'
        weather[year] = data

    return weather

def get_outputs(outputpath, years, shapenum):
    rootgrp = Dataset(outputpath, 'r', format='NETCDF4')
    outyears = list(rootgrp.variables['year'])
    outvars = [var for var in rootgrp.variables if len(rootgrp.variables[var].shape) == 2]
    print 'year,' + ','.join(outvars)
    
    outputs = {}
    for year in years:
        data = {var: rootgrp.variables[var][outyears.index(year), shapenum] for var in outvars}
        outputs[year] = data
        
        print ','.join([str(year)] + [str(data[var]) for var in outvars])

    return outputs
