import subprocess, csv, os
import numpy as np
import pandas as pd
import xarray as xr
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
                        if np.isnan(data[row[1]][ii]) and row[first_col+ii] != 'NA':
                            data[row[1]][ii] = float(row[first_col+ii])
                else:
                    data[row[1]] = map(lambda x: float(x) if x != 'NA' else np.nan, row[first_col:])

    return data

def excind(data, year, column):
    return data[str(year)][data['header'].index(column)]

def parse_csvv_line(line):
    line = line.rstrip().split(',')
    if len(line) == 1:
        line = line[0].split('\t')

    return line

def get_csvv(filepath, index0=None, indexend=None):
    csvv = {}
    with open(filepath, 'rU') as fp:
        printline = None
        for line in fp:
            if printline is not None:
                if printline == 'gamma':
                    csvv['gamma'] = map(float, parse_csvv_line(line))
                else:
                    csvv[printline] = map(lambda x: x.strip(), parse_csvv_line(line))

                if index0 is not None:
                    csvv[printline] = csvv[printline][index0:indexend]
                print ','.join(map(str, csvv[printline]))
                    
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
    else:
        return str(x)

def show_coefficient(csvv, preds, year, coefname, covartrans):
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

def get_weather(weathertemplate, years, shapenum, show_all_years=[], variable='tas', regindex='hierid', subset=None):
    weather = {}
    for year in years:
        filepath = weathertemplate.format('historical' if year < 2006 else 'rcp85', year)
        assert os.path.exists(filepath), "Cannot find %s" % filepath
        ds = xr.open_dataset(filepath)
        if isinstance(shapenum, str):
            regions = list(ds[regindex].values)
            shapenum = regions.index(shapenum)
            
        data = ds[variable].isel(**{regindex: shapenum})
        if subset is None:
            data = data.values
        else:
            data = data[subset].values

        if year in show_all_years:
            print str(year) + ': ' + ','.join(map(str, data))
        else:
            print str(year) + ': ' + ','.join(map(str, data[:10])) + '...'
        weather[year] = data

    return weather

def get_outputs(outputpath, years, shapenum, timevar='year'):
    rootgrp = Dataset(outputpath, 'r', format='NETCDF4')
    if isinstance(shapenum, str):
        regions = list(rootgrp.variables['regions'][:])
        shapenum = regions.index(shapenum)

    outyears = list(rootgrp.variables[timevar])
    outvars = [var for var in rootgrp.variables if len(rootgrp.variables[var].shape) == 2]
    print 'year,' + ','.join(outvars)
    
    outputs = {}
    for year in years:
        data = {var: rootgrp.variables[var][outyears.index(year), shapenum] for var in outvars}
        outputs[year] = data
        
        print ','.join([str(year)] + [str(data[var]) for var in outvars])

    return outputs

def get_region_data(filepath, region, indexcol='hierid'):
    df = pd.read_csv(filepath, index_col=indexcol)
    header = df.columns.values
    print ','.join(header)
    row = df.loc[region]
    print ','.join(map(str, row))

    return {header[ii]: row[ii] for ii in range(len(header))}
