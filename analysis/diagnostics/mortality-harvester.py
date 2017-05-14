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

lib.show_header("The Covariates File (allpreds):")
preds = lib.get_excerpt(os.path.join(dir, "mortality-allpreds.csv"), 3, 'IND.33.542.2153', [2009, futureyear-1, futureyear], onlymodel=onlymodel)

lib.show_header("The Result File (allcoeffs):")
coeffs = lib.get_excerpt(os.path.join(dir, "mortality-allcoeffs.csv"), 3, 'IND.33.542.2153', [2009, futureyear-1, futureyear], onlymodel=onlymodel)

lib.show_header("The Predictors File (allcalcs):")
calcs = lib.get_excerpt(os.path.join(dir, "mortality-allcalcs-" + onlymodel + ".csv"), 2, 'IND.33.542.2153', range(2001, 2011) + [futureyear-1, futureyear], hasmodel=False, hidecols=['postas2', 'postas3', 'postas4'])

lib.show_header("The Minimum Temperature Point File:")
shapenum = 0
with open(os.path.join(dir, onlymodel + "-polymins.csv"), 'r') as fp:
    reader = csv.reader(fp)
    header = reader.next()
    print ','.join(header)
    for row in reader:
        if row[0] == 'IND.33.542.2153':
            print ','.join(row)
            mintemps = {'header': header[1:], '2009': map(float, row[1:])}
            break
        shapenum += 1

lib.show_header("CSVV:")
csvv = lib.get_csvv(csvvpath, *csvvargs)

lib.show_header("Weather:")
weather = lib.get_weather(weathertemplate, range(2001, 2011) + [2050], shapenum)

for year in [2009, futureyear]:
    lib.show_header("Calc. of tas coefficient in %d (%f reported)" % (year, lib.excind(calcs, year-1, 'tas')))
    if use_mle:
        lib.show_coefficient_mle(csvv, preds, year, 'tas', {})
    else:
        lib.show_coefficient(csvv, preds, year, 'tas', {})

coefflist = ['tas'] + ['tas%d' % ii for ii in range(2, polypower + 1)]

lib.show_header("Calc. of minimum point temperature (%f reported)" % lib.excind(mintemps, 2009, 'analytic'))
curve = ZeroInterceptPolynomialCurve([-np.inf, np.inf], [lib.excind(calcs, 2009, coeff) for coeff in coefflist])
print ', '.join(["%f: %f" % (temp, curve(temp)) for temp in np.arange(10, 26)])

lib.show_header("Calc. of unclipped weather, first power (%f reported)" % lib.excind(calcs, year, 'postas'))
nonclipped = curve(weather[2009]) > curve(lib.excind(mintemps, 2009, 'analytic'))
lib.show_julia("%f / %d" % (sum(weather[2009][nonclipped]), sum(nonclipped)))

def get_preds(year):
    nonclipped = curve(weather[2009]) > curve(lib.excind(mintemps, 2009, 'analytic'))
    return ['%.12g' % sum(weather[year][nonclipped] ** power / sum(nonclipped)) for power in range(1, polypower+1)]

lib.show_header("Calc. of baseline (%f reported)" % (lib.excind(calcs, 2009, 'baseline')))
lines = []
for year in range(2001, 2011):
    lines.append("weather_%d = [%s]" % (year, ','.join(["%.12g" % weday for weday in weather[year]])))
lines.append("bl1(weather) = sum([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, 2009, coeff) for coeff in coefflist]))
lines.append("bl2(weather) = (bl1(exp((1:%d) * transpose(log(weather)))) - 365 * bl1(%.12g .^ (1:%d)))" % (polypower, lib.excind(mintemps, 2009, 'analytic'), polypower))
lines.append("bl(weather) = bl2(weather) .* (bl2(weather) .> 0)")
terms = []
for year in range(2001, 2011):
    terms.append("bl(weather_%d)" % (year))
lines.append("(" + ' + '.join(terms) + ") / 10")
lib.show_julia(lines)

lib.show_header("Calc. of result (%f reported)" % (coeffs[str(futureyear)][0]))

lib.show_header("  Without the goodmoney assumption:")
lines = ["weather_%d = [%s]" % (futureyear, ','.join(["%.12g" % weday for weday in weather[futureyear]])),
         "bl1(weather) = ([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, 2009, coeff) for coeff in coefflist]),
         "bl2(weather) = bl1(exp((1:%d) * transpose(log(weather)))) - bl1(%.12g .^ (1:%d))[1]" % (polypower, lib.excind(mintemps, 2009, 'analytic'), polypower),
         "bl(weather) = sum(bl2(weather) .* (bl2(weather) .> 0))",
         "bl(weather_%d)" % futureyear]
lib.show_julia(lines)

# What are the new coefficients
lib.show_header("  Marginal effect of money")
lines = ["gdpgammas = [%s]" % ', '.join(["%.12g" % csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['covarnames'][ii] == 'loggdppc']),
         "transpose(gdpgammas) * [%s]" % ', '.join(get_preds(futureyear))]
lib.show_julia(lines)

lines = ["gdpgammas = [%s]" % ', '.join(["%.12g" % csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['covarnames'][ii] == 'loggdppc']),
         "deltacoeff = gdpgammas .* (%.12g - %.12g)" % (lib.excind(preds, futureyear - 1, 'loggdppc'), lib.excind(preds, 2009, 'loggdppc')),
         "[%s] - deltacoeff" % ', '.join(["%.12g" % lib.excind(calcs, futureyear, coeff) for coeff in coefflist])]
lib.show_julia(lines)

lib.show_header("  Using the goodmoney alone")
lines = ["weather_%d = [%s]" % (futureyear, ','.join(["%.12g" % weday for weday in weather[futureyear]])),
         "gdpgammas = [%s]" % ', '.join(["%.12g" % csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['covarnames'][ii] == 'loggdppc']),
         "deltacoeff = gdpgammas .* (%.12g - %.12g)" % (lib.excind(preds, futureyear - 1, 'loggdppc'), lib.excind(preds, 2009, 'loggdppc')),
         "bl1(weather) = (([%s] - deltacoeff)' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, 2009, coeff) for coeff in coefflist]),
         "bl2(weather) = bl1(exp((1:%d) * transpose(log(weather)))) - bl1(%.12g .^ (1:%d))[1]" % (polypower, lib.excind(mintemps, 2009, 'analytic'), polypower),
         "bl(weather) = sum(bl2(weather) .* (bl2(weather) .> 0))",
         "bl(weather_%d)" % futureyear]
lib.show_julia(lines)

lib.show_header("  Using the goodmoney assumption")
lines = ["weather_%d = [%s]" % (futureyear, ','.join(["%.12g" % weday for weday in weather[futureyear]])),
         "bl1(weather) = ([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, 2009, coeff) for coeff in coefflist]),
         "bl2(weather) = bl1(exp((1:%d) * transpose(log(weather)))) - bl1(%.12g .^ (1:%d))[1]" % (polypower, lib.excind(mintemps, 2009, 'analytic'), polypower),
         "bl(weather) = bl2(weather) .* (bl2(weather) .> 0)",
         "original = bl(weather_%d)" % futureyear,
         "gdpgammas = [%s]" % ', '.join(["%.12g" % csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['covarnames'][ii] == 'loggdppc']),
         "deltacoeff = gdpgammas .* (%.12g - %.12g)" % (lib.excind(preds, futureyear - 1, 'loggdppc'), lib.excind(preds, 2009, 'loggdppc')),
         "bl1(weather) = (([%s] - deltacoeff)' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, 2009, coeff) for coeff in coefflist]),
         "bl2(weather) = bl1(exp((1:%d) * transpose(log(weather)))) - bl1(%.12g .^ (1:%d))[1]" % (polypower, lib.excind(mintemps, 2009, 'analytic'), polypower),
         "bl(weather) = bl2(weather) .* (bl2(weather) .> 0)",
         "goodmoney = bl(weather_%d)" % futureyear,
         "sum(min(original, goodmoney))"]
lib.show_julia(lines)
