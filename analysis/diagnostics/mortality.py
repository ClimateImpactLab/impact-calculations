import sys, os, csv
from netCDF4 import Dataset
import numpy as np
import lib

dir = sys.argv[1]

print "\nThe Covariates File (allpreds):"
preds = lib.get_excerpt(os.path.join(dir, "mortality-allpreds.csv"), 3, 'IND.33.542.2153', [2005, 2049])

print "\nThe Coefficients File (allbins):"
bins = lib.get_excerpt(os.path.join(dir, "mortality-allbins.csv"), 3, 'IND.33.542.2153', [2005, 2050])

print "\nThe Predictors File (allcalcs):"
calcs = lib.get_excerpt(os.path.join(dir, "mortality-allcalcs.csv"), 2, 'IND.33.542.2153', [2005])

print "\nCSVV:"
csvv = lib.get_csvv("/shares/gcp/social/parameters/mortality/mortality_single_stage_01192017/global_interaction_no_popshare_GMFD_b.csvv")

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
lib.show_julia(' + '.join(map(str, preds['2049'][0:11])))

for year in [2005, 2050]:
    print "\nCalc. of top bin coefficient in %d (%f reported)" % (year, bins[year][-1])
    lib.show_coefficient(year, 'bintas_32C_InfC', {'DayNumber-32-100': 'meandays_32C_InfC'})

print "\nCalc. of baseline (%f reported)" % (calcs['2005'][-1])
lines = ["bl(bins) = sum([%s]' * bins) / 100000" % ', '.join(map(lambda x: '0' if np.isnan(x) else str(x), bins['2005'][1:]))]
terms = []
for year in range(2001, 2011):
    terms.append("bl([%s])" % ', '.join(map(str, temps[year])))
lines.append("(" + ' + '.join(terms) + ") / 10")
lib.show_julia(lines)

print "\nCalc. of result (%f reported)" % (bins['2050'][0])
lines = ["ef(bins) = sum([%s]' * bins) / 100000" % ', '.join(map(lambda x: '0' if np.isnan(x) else str(x), bins['2050'][1:]))]
lines.append("ef([%s]) - %f" % (', '.join(map(str, temps[2050])), calcs['2005'][-1]))
lib.show_julia(lines)
