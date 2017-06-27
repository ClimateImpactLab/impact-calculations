import sys, os, csv
import numpy as np
from openest.models.curve import ZeroInterceptPolynomialCurve
import lib

futureyear = 2050
use_mle = False
use_goodmoney = True

polypower = 5

dir = sys.argv[1]
csvvpath = "/shares/gcp/social/parameters/mortality/Diagnostics_Apr17/global_interaction_Tmean-POLY-%d-AgeSpec.csvv" % polypower
weathertemplate = "/shares/gcp/climate/BCSD/aggregation/cmip5/IR_level/{0}/CCSM4/tas/tas_day_aggregated_{0}_r1i1p1_CCSM4_{1}.nc"
onlymodel = "global_interaction_Tmean-POLY-%d-AgeSpec-young" % polypower
csvvargs = (0, 3 * polypower) # (None, None)
region = 'IND.33.542.2153'
onlyreg = True # False

lib.show_header("The Covariates File (allpreds):")
preds = lib.get_excerpt(os.path.join(dir, "mortality-allpreds.csv"), 3, region, [2001, 2009, futureyear-1, futureyear], onlymodel=onlymodel)

lib.show_header("The Result File (allcoeffs):")
coeffs = lib.get_excerpt(os.path.join(dir, "mortality-allcoeffs.csv"), 3, region, [2009, futureyear-1, futureyear], onlymodel=onlymodel)

lib.show_header("The Predictors File (allcalcs):")
calcs = lib.get_excerpt(os.path.join(dir, "mortality-allcalcs-" + onlymodel + ".csv"), 2, region, range(2000, 2011) + [futureyear-1, futureyear], hasmodel=False)

lib.show_header("The Minimum Temperature Point File:")
shapenum = 0
with open(os.path.join(dir, onlymodel + "-polymins.csv"), 'r') as fp:
    reader = csv.reader(fp)
    header = reader.next()
    print ','.join(header)
    for row in reader:
        if row[0] == region:
            print ','.join(row)
            mintemps = {'header': header[1:], '2009': map(float, row[1:])}
            break
        shapenum += 1

lib.show_header("CSVV:")
csvv = lib.get_csvv(csvvpath, *csvvargs)

lib.show_header("Weather:")
weather = lib.get_weather(weathertemplate, range(2001, 2011) + [2049, 2050], shapenum)

lib.show_header("Outputs:")
outputs = lib.get_outputs(os.path.join(dir, onlymodel + '.nc4'), [2049, 2050], shapenum if not onlyreg else 0)

for year in [2001, futureyear]:
    lib.show_header("Calc. of tas coefficient in %d (%f reported)" % (year, lib.excind(calcs, year-1, 'tas')))
    if use_mle:
        lib.show_coefficient_mle(csvv, preds, year, 'tas', {})
    else:
        lib.show_coefficient(csvv, preds, year, 'tas', {})

coefflist = ['tas'] + ['tas%d' % ii for ii in range(2, polypower + 1)]

lib.show_header("Calc. of minimum point temperature (%f reported)" % lib.excind(mintemps, 2009, 'analytic'))
curve = ZeroInterceptPolynomialCurve([-np.inf, np.inf], [lib.excind(calcs, 2000, coeff) for coeff in coefflist])
print ', '.join(["%f: %f" % (temp, curve(temp)) for temp in np.arange(10, 26)])

def get_preds(year):
    nonclipped = curve(weather[year]) > curve(lib.excind(mintemps, 2009, 'analytic'))
    return ['%.12g' % sum(weather[year][nonclipped] ** power / sum(nonclipped)) for power in range(1, polypower+1)]

lib.show_header("Calc. of baseline (%f reported)" % (lib.excind(calcs, 2000, 'baseline')))
lines = []
for year in range(2001, 2011):
    lines.append("weather_%d = [%s]" % (year, ','.join(["%.12g" % weday for weday in weather[year]])))
lines.append("bl1(weather) = sum([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, 2000, coeff) for coeff in coefflist]))
lines.append("bl2(weather) = (bl1(exp((1:%d) * transpose(log(weather)))) - 365 * bl1(%.12g .^ (1:%d)))" % (polypower, lib.excind(mintemps, 2009, 'analytic'), polypower))
lines.append("bl(weather) = bl2(weather) .* (bl2(weather) .> 0)")
terms = []
for year in range(2001, 2011):
    terms.append("bl(weather_%d)" % (year))
lines.append("(" + ' + '.join(terms) + ") / 10")
lib.show_julia(lines)

lib.show_header("Calc. of clipped days portion (%f reported)" % lib.excind(calcs, 2050, 'zero'))
lines = ["weather_%d = [%s]" % (2050, ','.join(["%.12g" % weday for weday in weather[2050]])),
         "bl1(weather) = ([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, 2049, coeff) for coeff in coefflist]),
         "bl2(weather) = bl1(exp((1:%d) * transpose(log(weather)))) - bl1(%.12g .^ (1:%d))[1]" % (polypower, lib.excind(mintemps, 2009, 'analytic'), polypower),
         "mean(bl2(weather_%d) .<= 0)" % 2050]
lib.show_julia(lines)

lib.show_header("Calc. of result (%f reported)" % (coeffs[str(futureyear)][0]))

lib.show_header("  Without the goodmoney assumption:")
lines = ["weather_%d = [%s]" % (futureyear, ','.join(["%.12g" % weday for weday in weather[futureyear]])),
         "bl1(weather) = ([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, futureyear, coeff) for coeff in coefflist]),
         "bl2(weather) = bl1(exp((1:%d) * transpose(log(weather)))) - bl1(%.12g .^ (1:%d))[1]" % (polypower, lib.excind(mintemps, 2009, 'analytic'), polypower),
         "bl(weather) = sum(bl2(weather) .* (bl2(weather) .> 0))",
         "bl(weather_%d) - %.12g" % (futureyear, lib.excind(calcs, 2000, 'baseline'))]
lib.show_julia(lines)

lib.show_header("  Using the baseline curve only")
lines = ["weather_%d = [%s]" % (futureyear, ','.join(["%.12g" % weday for weday in weather[futureyear]])),
         "bl1(weather) = ([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, 2000, coeff) for coeff in coefflist]),
         "bl2(weather) = bl1(exp((1:%d) * transpose(log(weather)))) - bl1(%.12g .^ (1:%d))[1]" % (polypower, lib.excind(mintemps, 2009, 'analytic'), polypower),
         "bl(weather) = sum(bl2(weather) .* (bl2(weather) .> 0))",
         "bl(weather_%d) - %.12g" % (futureyear, lib.excind(calcs, 2000, 'baseline'))]
lib.show_julia(lines)

lib.show_header("  Using the no-anti-adaptation assumption")
lines = ["weather_%d = [%s]" % (futureyear, ','.join(["%.12g" % weday for weday in weather[futureyear]])),
         "bl1(weather) = ([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, futureyear, coeff) for coeff in coefflist]),
         "bl2(weather) = bl1(exp((1:%d) * transpose(log(weather)))) - bl1(%.12g .^ (1:%d))[1]" % (polypower, lib.excind(mintemps, 2009, 'analytic'), polypower),
         "bl(weather) = bl2(weather) .* (bl2(weather) .> 0)",
         "original = bl(weather_%d)" % futureyear,
         "bl1(weather) = ([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, 2000, coeff) for coeff in coefflist]),
         "bl2(weather) = bl1(exp((1:%d) * transpose(log(weather)))) - bl1(%.12g .^ (1:%d))[1]" % (polypower, lib.excind(mintemps, 2009, 'analytic'), polypower),
         "bl(weather) = bl2(weather) .* (bl2(weather) .> 0)",
         "goodmoney = bl(weather_%d)" % futureyear,
         "sum(min(original, goodmoney)) - %.12g" % lib.excind(calcs, 2000, 'baseline')]
lib.show_julia(lines)

lib.show_header("Climtas effect in %d (%f reported)" % (2050, outputs[2050]['climtas_effect']))
coeffs = [csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['covarnames'][ii] == 'climtas']
lines = ["weather_%d = [%s]" % (2050, ','.join(["%.12g" % weday for weday in weather[2050]])),
         "bl1(weather) = ([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, 2050, coeff) for coeff in coefflist]), # NOTE: coeffs from 2050, ot 2049
         "bl2(weather) = bl1(exp((1:%d) * transpose(log(weather)))) - bl1(%.12g .^ (1:%d))[1]" % (polypower, lib.excind(mintemps, 2009, 'analytic'), polypower),
         "unclipped = bl2(weather_%d) .> 0" % 2050,
         "(" + ' + '.join(["%s * sum((weather_%d.^%d - %.12f^%d) .* unclipped')" % (coeffs[kk], 2050, kk+1, lib.excind(mintemps, 2009, 'analytic'), kk+1) for kk in range(5)]) + ")"]
lib.show_julia(lines, clipto=400)

