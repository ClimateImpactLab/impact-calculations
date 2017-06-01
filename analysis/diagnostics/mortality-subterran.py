import sys, os, csv
import numpy as np
from openest.models.curve import CubicSplineCurve
import lib

futureyear = 2050
use_goodmoney = True

knots = [-10, 0, 10, 20, 28, 33]

dir = sys.argv[1]
csvvpath = "/shares/gcp/social/parameters/mortality/Diagnostics_Apr17/global_interaction_Tmean-CSpline-LS-AgeSpec.csvv"
weathertemplate = "/shares/gcp/climate/BCSD/aggregation/cmip5/IR_level/{0}/CCSM4/tas/tas_day_aggregated_{0}_r1i1p1_CCSM4_{1}.nc"
onlymodel = "global_interaction_Tmean-CSpline-LS-AgeSpec-young"
csvvargs = (0, 3 * 4)

lib.show_header("The Covariates File (allpreds):")
preds = lib.get_excerpt(os.path.join(dir, "mortality-allpreds.csv"), 3, 'IND.33.542.2153', [2009, futureyear-1, futureyear], onlymodel=onlymodel)

lib.show_header("The Predictors File (allcalcs):")
calcs = lib.get_excerpt(os.path.join(dir, "mortality-allcalcs-" + onlymodel + ".csv"), 2, 'IND.33.542.2153', range(2001, 2011) + [futureyear], hasmodel=False)

lib.show_header("The Minimum Temperature Point File:")
shapenum = 0
with open(os.path.join(dir, onlymodel + "-splinemins.csv"), 'r') as fp:
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
    lib.show_header("Calc. of spline_variables-0 coefficient in %d (%f reported)" % (year, lib.excind(calcs, year, 'spline_variables-0')))
    lib.show_coefficient(csvv, preds, year, 'spline_variables-0', {})

coefflist = ['spline_variables-%d' % ii for ii in range(0, 5)]

lib.show_header("Calc. of minimum point temperature (%f reported)" % lib.excind(mintemps, 2009, 'analytic'))
curve = CubicSplineCurve(knots, [lib.excind(calcs, 2009, coeff) for coeff in coefflist])
print ', '.join(["%f: %f" % (temp, curve(temp)) for temp in np.arange(10, 26)])

lib.show_header("Calc. of baseline (%f reported)" % (lib.excind(calcs, 2009, 'baseline')))
lines = ["bl1(weather) = sum([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, 2009, coeff) for coeff in coefflist]),
         "bl(weather) = max(0, bl1(weather) - bl1([%s]))" % (', '.join(["%d" % term for term in curve.get_terms(lib.excind(mintemps, 2009, 'analytic'))]))]
terms = []
for year in range(2001, 2011):
    terms.append("bl([%s])" % ', '.join(["%.12g" % tas for tas in weather[year]]))
lines.append("(" + ' + '.join(terms) + ") / 10")
lib.show_julia(lines)

lib.show_header("Calc. of result (%f reported)" % (calcs[str(futureyear)][0]))
## Without goodmoney
lib.show_header("  Without the goodmoney assumption")
lines = ["ef1(weather) = sum([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, futureyear, coeff) for coeff in coefflist]),
        "ef(weather) = ef1(weather) - ef1(365 * [%s])" % (', '.join(["%d" % term for term in curve.get_terms(lib.excind(mintemps, 2009, 'analytic'))]))]
lines.append("ef([%s]) - %f" % (', '.join(["%.12g" % tas for tas in weather[futureyear]]), lib.excind(calcs, futureyear, 'baseline')))
lib.show_julia(lines)

if use_goodmoney:
    ## Check for goodmoney problem
    lib.show_header("  Marginal effect of money")
    lines = ["gdpgammas = [%s]" % ', '.join(["%.12g" % csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['covarnames'][ii] == 'loggdppc']),
             "transpose(gdpgammas) * [%s]" % ', '.join(["%.12g" % tas for tas in weather[futureyear]])]
    lib.show_julia(lines)

    # ## What are the new coefficients
    # lines = ["gdpgammas = [%s]" % ', '.join(["%.12g" % csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['covarnames'][ii] == 'loggdppc']),
    #          "deltacoeff = gdpgammas .* (%.12g - %.12g)" % (lib.excind(preds, futureyear - 1, 'loggdppc'), lib.excind(preds, 2009, 'loggdppc')),
    #          "[%s] - deltacoeff" % ', '.join(["%.12g" % lib.excind(calcs, futureyear, coeff) for coeff in coefflist])]
    # lib.show_julia(lines)

    # ## Check components
    # lines = ["gdpgammas = [%s]" % ', '.join(["%.12g" % csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['covarnames'][ii] == 'loggdppc']),
    #          "deltacoeff = gdpgammas .* (%.12g - %.12g)" % (lib.excind(preds, futureyear - 1, 'loggdppc'), lib.excind(preds, 2009, 'loggdppc')),
    #          "ef1(weather) = sum(([%s] - deltacoeff)' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, futureyear, coeff) for coeff in coefflist]),
    #          "ef1([%s]) * 100000" % ', '.join(["%.12g" % tas for tas in weather[futureyear]])]
    # lib.show_julia(lines)

    # lines = ["gdpgammas = [%s]" % ', '.join(["%.12g" % csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['covarnames'][ii] == 'loggdppc']),
    #          "deltacoeff = gdpgammas .* (%.12g - %.12g)" % (lib.excind(preds, futureyear - 1, 'loggdppc'), lib.excind(preds, 2009, 'loggdppc')),
    #          "ef1(weather) = sum(([%s] - deltacoeff)' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, futureyear, coeff) for coeff in coefflist]),
    #          "ef1(365 * [%s]) * 100000" % (', '.join(["%d" % term for term in curve.get_terms(lib.excind(mintemps, 2009, 'analytic'))]))]
    # lib.show_julia(lines)

    ## Return coefficients to baseline
    lib.show_header("  Using the goodmoney assumption")
    lines = ["gdpgammas = [%s]" % ', '.join(["%.12g" % csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['covarnames'][ii] == 'loggdppc']),
             "deltacoeff = gdpgammas .* (%.12g - %.12g)" % (lib.excind(preds, futureyear - 1, 'loggdppc'), lib.excind(preds, 2009, 'loggdppc')),
             "ef1(weather) = sum(([%s] - deltacoeff)' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, futureyear, coeff) for coeff in coefflist]),
             "ef(weather) = ef1(weather) - ef1(365 * [%s])" % (', '.join(["%d" % term for term in curve.get_terms(lib.excind(mintemps, 2009, 'analytic'))])),
             "ef([%s]) - %f" % (', '.join(["%.12g" % tas for tas in weather[futureyear]]), lib.excind(calcs, futureyear, 'baseline'))]
    lib.show_julia(lines)
