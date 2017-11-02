import sys, os, csv
import numpy as np
from openest.models.curve import ZeroInterceptPolynomialCurve
import lib

futureyear = 2050
polypower = 4

dir = sys.argv[1]
onlymodel = "pr1_BEST_poly4_electricity_RESIDENT_model4"
csvvpath = "/shares/gcp/social/parameters/energy/projection1/%s.csvv" % onlymodel
weathertemplate = "/shares/gcp/climate/BCSD/aggregation/cmip5/IR_level/{0}/CCSM4/tas/tas_day_aggregated_{0}_r1i1p1_CCSM4_{1}.nc"
region = 'USA.14.608' #'IND.33.542.2153'
onlyreg = True

lib.show_header("The Covariates File (allpreds):")
preds = lib.get_excerpt(os.path.join(dir, "allmodels-allpreds.csv"), 3, region, [2001, 2009, futureyear-1, futureyear], onlymodel=onlymodel)

lib.show_header("The Predictors File (allcalcs):")
calcs = lib.get_excerpt(os.path.join(dir, "allmodels-allcalcs-" + onlymodel + ".csv"), 2, region, range(2000, 2011) + [futureyear-1, futureyear], hasmodel=False)

shapenum = 0
with open(os.path.join("/shares/gcp/regions/hierarchy-flat.csv"), 'r') as fp:
    reader = csv.reader(fp)
    header = reader.next()
    for row in reader:
        if row[0] == region:
            shapenum = int(row[header.index('agglomid')]) - 1
            break
        
lib.show_header("CSVV:")
csvv = lib.get_csvv(csvvpath)

lib.show_header("Weather:")
weather = lib.get_weather(weathertemplate, range(2001, 2011) + [2049, 2050], shapenum)

lib.show_header("Outputs:")
outputs = lib.get_outputs(os.path.join(dir, onlymodel + '.nc4'), [2049, 2050], shapenum if not onlyreg else 0)

def make_make_incbin(ii):
    def make_incbin(preds, predyear):
        return np.digitize(lib.excind(preds, predyear, 'loggdppc'), [ -np.inf, 7.427, 7.941, 8.355, 8.706, 9.015, 9.309, 9.634, 9.993, 10.390, np.inf ]) == ii
    return make_incbin

def make_make_climtasincbin(ii):
    def make_climtasincbin(preds, predyear):
        return lib.excind(preds, predyear, 'climtas') * (np.digitize(lib.excind(preds, predyear, 'loggdppc'), [ -np.inf, 7.427, 7.941, 8.355, 8.706, 9.015, 9.309, 9.634, 9.993, 10.390, np.inf ]) == ii)
    return make_climtasincbin

for year in [2001, futureyear]:
    lib.show_header("Calc. of tas coefficient in %d (%f reported)" % (year, lib.excind(calcs, year-1, 'coeff-tas')))
    allcovars = {'incbin' + str(ii): make_make_incbin(ii) for ii in range(1, 11)}
    allcovars.update({'climtas*incbin' + str(ii): make_make_climtasincbin(ii) for ii in range(1, 11)})
    lib.show_coefficient(csvv, preds, year, 'tas', allcovars)

coefflist = ['coeff-tas'] + ['coeff-tas%d' % ii for ii in range(2, polypower + 1)]

lib.show_header("Calc. of baseline (%f reported)" % (lib.excind(calcs, 2000, 'baseline')))
lines = []
for year in range(2001, 2011):
    lines.append("weather_%d = [%s]" % (year, ','.join(["%.12g" % weday for weday in weather[year]])))
lines.append("bl1(weather) = sum([%s]' * weather)" % ', '.join(["%.12g" % lib.excind(calcs, 2000, coeff) for coeff in coefflist]))
lines.append("bl2(weather) = bl1([%s])" % '; '.join(["weather'.^%d" % pow for pow in range(1, polypower+1)]))
terms = []
for year in range(2001, 2011):
    terms.append("bl2(weather_%d)" % (year))
lines.append("(" + ' + '.join(terms) + ") / 10")
lib.show_julia(lines)

lib.show_header("Calc. of result (%f reported)" % (outputs[futureyear]['rebased']))

lines = ["weather_%d = [%s]" % (futureyear, ','.join(["%.12g" % weday for weday in weather[futureyear]])),
         "eff1(weather) = sum([%s]' * weather)" % ', '.join(["%.12g" % lib.excind(calcs, futureyear, coeff) for coeff in coefflist]),
         "eff2(weather) = eff1([%s])" % ('; '.join(["weather'.^%d" % pow for pow in range(1, polypower+1)]))]
lines.append("eff2(weather_%d) - %.12g" % (futureyear, lib.excind(calcs, 2000, 'baseline')))
lib.show_julia(lines)
