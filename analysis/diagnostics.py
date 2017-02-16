import sys, os, csv, subprocess
from netCDF4 import Dataset
import numpy as np

def show_julia(command):
    if isinstance(command, str):
        print command
        print "# " + subprocess.check_output(["julia", "-e", "println(" + command + ")"])
    else:
        print "\n".join(command)
        print "# " + subprocess.check_output(["julia", "-e", "; ".join(command[:-1]) + "; println(" + command[-1] + ")"])

dir = sys.argv[1]

print "\nThe Covariates File (allpreds):"

preds = {}
with open(os.path.join(dir, "mortality-allpreds.csv"), 'r') as fp:
    header = fp.readline().rstrip()
    preds['header'] = header.split(',')[3:]
    print header
    print "..."
    for line in fp:
        if line[:len('IND.33.542.2153,XXXX')] in ['IND.33.542.2153,2005', 'IND.33.542.2153,2049']:
            print line.rstrip()
            print "..."
            preds[line[len('IND.33.542.2153,'):len('IND.33.542.2153,XXXX')]] = map(float, line.split(',')[3:])

print "\nThe Coefficients File (allbins):"

bins = {}
with open(os.path.join(dir, "mortality-allbins.csv"), 'r') as fp:
    print fp.readline().rstrip()
    print "..."
    for line in fp:
        if line[:len('IND.33.542.2153,XXXX')] in ['IND.33.542.2153,2005', 'IND.33.542.2153,2050']:
            print line.rstrip()
            print "..."
            bins[line[len('IND.33.542.2153,'):len('IND.33.542.2153,XXXX')]] = map(float, line.split(',')[3:])

print "\nThe Predictors File (allcalcs):"

calcs = {}
with open(os.path.join(dir, "mortality-allcalcs.csv"), 'r') as fp:
    print fp.readline().rstrip()
    print "..."
    for line in fp:
        if line[:len('IND.33.542.2153,XXXX')] in ['IND.33.542.2153,2005']:
            print line.rstrip()
            print "..."
            calcs[line[len('IND.33.542.2153,'):len('IND.33.542.2153,XXXX')]] = map(float, line.split(',')[2:])

print "\nCSVV:"

csvv = {}
with open("/shares/gcp/social/parameters/mortality/mortality_single_stage_01192017/global_interaction_no_popshare_GMFD_b.csvv", 'r') as fp:
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

print "\nTemperature Bin Values:"

# Load regions
mapping = {} # color to hierid

with open("/shares/gcp/regions/hierarchy.csv", 'r') as fp:
    for line in fp:
        if line[0] != '#':
            break

    reader = csv.reader(fp)
    for row in reader:
        if row[0] == 'IND.33.542.2153':
            regionid = int(row[6]) - 1
            break

temps = {}
for year in range(2001, 2011) + [2050]:
    if year < 2006:
        rootgrp = Dataset("/shares/gcp/climate/BCSD/aggregation/cmip5_bins_new/IR_level/historical/CCSM4/tas/tas_Bindays_aggregated_historical_r1i1p1_CCSM4_%d.nc" % year, 'r', format='NETCDF4')
    else:
        rootgrp = Dataset("/shares/gcp/climate/BCSD/aggregation/cmip5_bins_new/IR_level/rcp85/CCSM4/tas/tas_Bindays_aggregated_rcp85_r1i1p1_CCSM4_%d.nc" % year, 'r', format='NETCDF4')

    weather = rootgrp.variables['DayNumber'][:, :, regionid]
    print str(year) + ': ' + str(list(np.sum(weather, axis=0)))
    temps[year] = list(np.sum(weather, axis=0))

print "\nSum of mean days in 2049 (365):"
show_julia(' + '.join(map(str, preds['2049'][0:11])))

for year in ['2005', '2050']:
    print "\nCalc. of top bin coefficient in %s (%f reported)" % (year, bins[year][-1])

    predyear = '2049' if year == '2050' else year
    terms = []
    for ii in range(len(csvv['gamma'])):
        if csvv['prednames'][ii] == 'bintas_32C_InfC':
            if csvv['covarnames'][ii] == '1':
                terms.append(str(csvv['gamma'][ii]))
            elif csvv['covarnames'][ii] == 'DayNumber-32-100':
                terms.append(str(csvv['gamma'][ii]) + " * " + str(preds[predyear][preds['header'].index('meandays_32C_InfC')]))
            else:
                terms.append(str(csvv['gamma'][ii]) + " * " + str(preds[predyear][preds['header'].index(csvv['covarnames'][ii])]))
    show_julia(' + '.join(terms))

print "\nCalc. of baseline (%f reported)" % (calcs['2005'][-1])
lines = ["bl(bins) = sum([%s]' * bins) / 100000" % ', '.join(map(lambda x: '0' if np.isnan(x) else str(x), bins['2005'][1:]))]
terms = []
for year in range(2001, 2011):
    terms.append("bl([%s])" % ', '.join(map(str, temps[year])))
lines.append("(" + ' + '.join(terms) + ") / 10")
show_julia(lines)

print "\nCalc. of result (%f reported)" % (bins['2050'][0])
lines = ["ef(bins) = sum([%s]' * bins) / 100000" % ', '.join(map(lambda x: '0' if np.isnan(x) else str(x), bins['2050'][1:]))]
lines.append("ef([%s]) - %f" % (', '.join(map(str, temps[2050])), calcs['2005'][-1]))
show_julia(lines)
