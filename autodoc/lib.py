import subprocess, csv, os
import numpy as np
import pandas as pd
import xarray as xr
from netCDF4 import Dataset

def show_header(text):
    print(("\n\033[1m" + text + "\033[0m"))

def show_julia(command, clipto=160):
    if isinstance(command, str):
        print(command)
        try:
            print("# " + subprocess.check_output(["julia", "-e", "println(" + command + ")"]).decode("utf-8"))
        except Exception as ex:
            print(ex)
    else:
        for line in command:
            if clipto is not None and len(line) > clipto:
                print((line[:(clipto-3)] + '...'))
            else:
                print(line)

        try:
            print("# " + subprocess.check_output(["julia", "-e", "; ".join(command[:-1]) + "; println(" + command[-1] + ")"]).decode("utf-8"))
        except Exception as ex:
            print(ex)

def get_julia(obj):
    if isinstance(obj, float):
        return "%f" % obj
    elif isinstance(obj, np.ndarray):
        return "[%s]" % (', '.join(map(get_julia, obj)))
    else:
        return str(obj)

def get_excerpt(filepath, first_col, regionid, years, hasmodel=True, onlymodel=None, hidecols=[]):
    data = {}
    model = None
    with open(filepath, 'r') as fp:
        for line in fp:
            if line.rstrip() == '...':
                break
        reader = csv.reader(fp)
        header = next(reader)
        data['header'] = header[first_col:]
        # Find columns to hide
        showcols = np.array([col not in hidecols for col in header])
        
        print((','.join(np.array(header)[showcols])))
        print("...")
        for row in reader:
            if 'e+06' in row[1]:
                row[1] = str(int(float(row[1]) / 1000))
            if '.' in row[1]:
                row[1] = str(int(float(row[1])))
            if row[0] == regionid and row[1] in list(map(str, years)):
                if hasmodel:
                    if onlymodel is not None and row[2] != onlymodel:
                        continue
                    if model is None:
                        model = row[2]
                    elif model != row[2]:
                        break
                print((','.join(np.array(row)[showcols[:len(row)]])))
                if int(row[1]) + 1 not in years:
                    print("...")
                if row[1] in data:
                    # Just fill in NAs (until we figure out why dubling up lines)
                    for ii in range(len(data[row[1]])):
                        if np.isnan(data[row[1]][ii]) and row[first_col+ii] != 'NA':
                            data[row[1]][ii] = pflt(row[first_col+ii])
                else:
                    data[row[1]] = [pflt(x) if x != 'NA' else np.nan for x in row[first_col:]]

    return data

def excind(data, year, column):
    if 'header' in data:
        return data[str(year)][data['header'].index(column)]
    else:
        return data[str(year)][column]

def parse_csvv_line(line):
    line = line.rstrip().split(',')
    if len(line) == 1:
        line = line[0].split('\t')

    return line

def get_csvv(filepath, index0=None, indexend=None, fracsubset=(0, 1)):
    csvv = {}
    with open(filepath, 'rU') as fp:
        printline = None
        for line in fp:
            if printline is not None:
                if printline == 'gamma':
                    csvv['gamma'] = list(map(float, parse_csvv_line(line)))
                else:
                    csvv[printline] = [x.strip() for x in parse_csvv_line(line)]

                if fracsubset != (0, 1) and index0 is None:
                    index0 = fracsubset[0] * len(csvv[printline]) / fracsubset[1]
                    indexend = (fracsubset[0] + 1) * len(csvv[printline]) / fracsubset[1]

                if index0 is not None:
                    csvv[printline] = csvv[printline][index0:indexend]
                print((','.join(map(str, csvv[printline]))))
                    
                printline = None
            if line.rstrip() in ["prednames", "covarnames", "gamma"]:
                printline = line.rstrip()

    return csvv

def get_gamma(csvv, predname, covarname):
    for ii in range(len(csvv['gamma'])):
        if csvv['prednames'][ii] == predname and csvv['covarnames'][ii] == covarname:
            return csvv['gamma'][ii]

    return None

def jstr(x):
    if x == True:
        return 'true'
    elif x == False:
        return 'false'
    elif x == np.inf:
        return 'Inf'
    elif x == -np.inf:
        return '-Inf'
    else:
        return str(x)

def pflt(x):
    if x == 'True' or x == 'true':
        return 1.
    if x == 'False' or x == 'false':
        return 0.
    if x[0] == '[' and x[-1] == ']':
        return np.array(list(map(float, x[1:-1].split())))
    return float(x)
    
def show_coefficient(csvv, preds, year, coefname, covartrans={}, betalimits=None):
    predyear = year - 1 if year > 2015 else year

    terms = []
    for ii in range(len(csvv['gamma'])):
        if csvv['prednames'][ii] == coefname:
            if csvv['covarnames'][ii] == '1':
                terms.append(str(csvv['gamma'][ii]))
            elif csvv['covarnames'][ii] in covartrans:
                if covartrans[csvv['covarnames'][ii]] is None:
                    continue # Skip this one
                if callable(covartrans[csvv['covarnames'][ii]]):
                    terms.append(str(csvv['gamma'][ii]) + " * " + jstr(covartrans[csvv['covarnames'][ii]](preds, predyear)))
                else:
                    terms.append(str(csvv['gamma'][ii]) + " * " + jstr(excind(preds, predyear, covartrans[csvv['covarnames'][ii]])))
            else:
                terms.append(str(csvv['gamma'][ii]) + " * " + jstr(excind(preds, predyear, csvv['covarnames'][ii])))

    if betalimits is not None:
        show_julia("min(max(%s, %s), %s)" % (jstr(betalimits[0]), ' + '.join(terms), jstr(betalimits[1])))
    else:
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

def get_adm0_regionindices(adm0):
    with open("/shares/gcp/regions/hierarchy.csv", 'r') as fp:
        for line in fp:
            if line[0] != '#':
                break

        reader = csv.reader(fp)
        for row in reader:
            if row[0][:3] == adm0 and row[6] != '':
                yield int(row[6]) - 1

def get_outputs(outputpath, years, shapenum, timevar='year', deltamethod=False):
    rootgrp = Dataset(outputpath, 'r', format='NETCDF4')
    if isinstance(shapenum, str):
        regions = list(rootgrp.variables['regions'][:])
        shapenum = regions.index(shapenum)
    elif len(rootgrp.variables['regions']) == 1:
        shapenum = 0
        
    outyears = list(rootgrp.variables[timevar])
    outvars = [var for var in rootgrp.variables if len(rootgrp.variables[var].shape) == 2 and var != 'vcv']
    print(('year,' + ','.join(outvars)))
    
    outputs = {}
    for year in years:
        data = {var: rootgrp.variables[var][outyears.index(year), shapenum] for var in outvars}
        outputs[year] = data
        if deltamethod:
            for var in outvars:
                outputs[year][var + '_bcde'] = rootgrp.variables[var + '_bcde'][:, outyears.index(year), shapenum]
            outputs['vcv'] = rootgrp.variables['vcv']
            
        print((','.join([str(year)] + [str(data[var]) for var in outvars])))

    return outputs

def get_region_data(filepath, region, indexcol='hierid'):
    df = pd.read_csv(filepath, index_col=indexcol)
    header = df.columns.values
    print((','.join(header)))
    row = df.loc[region]
    print((','.join(map(str, row))))

    return {header[ii]: row[ii] for ii in range(len(header))}

def find_betalimits(config):
    if isinstance(config, list):
        betalimits = {}
        for ii in range(len(config)):
            if isinstance(config[ii], list) or isinstance(config[ii], dict):
                betalimits.update(find_betalimits(config[ii]))
        return betalimits

    if 'beta-limits' in config:
        betalimits = {key: list(map(float, config['beta-limits'][key].split(','))) for key in config['beta-limits']}
    else:
        betalimits = {}

    for key in config:
        if isinstance(config[key], list) or isinstance(config[key], dict):
            betalimits.update(find_betalimits(config[key]))

    return betalimits
