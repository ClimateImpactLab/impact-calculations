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

print "SHAPENUM: " + str(shapenum)
        
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
lines = ["bl1(weather) = sum([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, 2009, coeff) for coeff in coefflist]),
         "bl(weather) = 365 * (bl1(weather) - bl1(%.12g .^ (1:%d)))" % (lib.excind(mintemps, 2009, 'analytic'), polypower)]
terms = []
for year in range(2001, 2011):
    terms.append("bl([%s])" % ','.join(get_preds(year)))
lines.append("(" + ' + '.join(terms) + ") / 10")
lib.show_julia(lines)

lib.show_header("Calc. of result (%f reported)" % (coeffs[str(futureyear)][0]))
## Without goodmoney
lib.show_header("  Without the goodmoney assumption")
lines = ["ef1(weather) = sum([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, futureyear, coeff) for coeff in coefflist]),
         "ef(weather) = 365 * (ef1(weather) - ef1(%.12f .^ (1:%d)))" % (lib.excind(mintemps, 2009, 'analytic'), polypower)]
lines.append("ef([%s]) - %f" % (','.join(get_preds(futureyear)), lib.excind(calcs, futureyear, 'baseline')))
lib.show_julia(lines)

if use_goodmoney:
    ## Check for goodmoney problem
    lib.show_header("  Marginal effect of money")
    lines = ["gdpgammas = [%s]" % ', '.join(["%.12g" % csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['covarnames'][ii] == 'loggdppc']),
             "transpose(gdpgammas) * [%s]" % ', '.join(get_preds(futureyear))]
    lib.show_julia(lines)

    # ## What are the new coefficients
    lines = ["gdpgammas = [%s]" % ', '.join(["%.12g" % csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['covarnames'][ii] == 'loggdppc']),
             "deltacoeff = gdpgammas .* (%.12g - %.12g)" % (lib.excind(preds, futureyear - 1, 'loggdppc'), lib.excind(preds, 2009, 'loggdppc')),
             "[%s] - deltacoeff" % ', '.join(["%.12g" % lib.excind(calcs, futureyear, coeff) for coeff in coefflist])]
    lib.show_julia(lines)

    # ## Check components
    lines = ["gdpgammas = [%s]" % ', '.join(["%.12g" % csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['covarnames'][ii] == 'loggdppc']),
             "deltacoeff = gdpgammas .* (%.12g - %.12g)" % (lib.excind(preds, futureyear - 1, 'loggdppc'), lib.excind(preds, 2009, 'loggdppc')),
             "ef1(weather) = sum(([%s] - deltacoeff)' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, futureyear, coeff) for coeff in coefflist]),
             "ef1([%s]) * 100000" % ', '.join(get_preds(futureyear))]
    lib.show_julia(lines)

    ## Return coefficients to baseline
    lib.show_header("  Using the goodmoney assumption")
    lines = ["gdpgammas = [%s]" % ', '.join(["%.12g" % csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['covarnames'][ii] == 'loggdppc']),
             "deltacoeff = gdpgammas .* (%.12g - %.12g)" % (lib.excind(preds, futureyear - 1, 'loggdppc'), lib.excind(preds, 2009, 'loggdppc')),
             "ef1(weather) = sum(([%s] - deltacoeff)' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, futureyear, coeff) for coeff in coefflist]),
             "ef(weather) = ef1(365 * weather) - ef1(365 * [%s])" % (', '.join(["%.12g" % term for term in np.power(lib.excind(mintemps, 2009, 'analytic'), np.arange(1, polypower+1))])),
             "ef([%s]) - %f" % (', '.join(get_preds(futureyear)), lib.excind(calcs, futureyear, 'baseline'))]
    lib.show_julia(lines)
