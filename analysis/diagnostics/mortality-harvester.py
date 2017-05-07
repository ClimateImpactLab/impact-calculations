import sys, os, csv
import numpy as np
from openest.models.curve import ZeroInterceptPolynomialCurve
import lib

futureyear = 2050
use_mle = False
use_goodmoney = True

dir = sys.argv[1]
csvvpath = "/shares/gcp/social/parameters/mortality/Diagnostics_Apr17/global_interaction_Tmean-POLY-4-AgeSpec.csvv"
onlymodel = "global_interaction_Tmean-POLY-4-AgeSpec-kid"
csvvargs = (0, 12) # (None, None)

lib.show_header("The Covariates File (allpreds):")
preds = lib.get_excerpt(os.path.join(dir, "mortality-allpreds.csv"), 3, 'IND.33.542.2153', [2009, futureyear-1, futureyear], onlymodel=onlymodel)

lib.show_header("The Result File (allcoeffs):")
coeffs = lib.get_excerpt(os.path.join(dir, "mortality-allcoeffs.csv"), 3, 'IND.33.542.2153', [2009, futureyear-1, futureyear], onlymodel=onlymodel)

lib.show_header("The Predictors File (allcalcs):")
calcs = lib.get_excerpt(os.path.join(dir, "mortality-allcalcs-" + onlymodel + ".csv"), 2, 'IND.33.542.2153', range(2001, 2011) + [futureyear-1, futureyear], hasmodel=False)

lib.show_header("The Minimum Temperature Point File:")
with open(os.path.join(dir, onlymodel + "-polymins.csv"), 'r') as fp:
    reader = csv.reader(fp)
    header = reader.next()
    print ','.join(header)
    for row in reader:
        if row[0] == 'IND.33.542.2153':
            print ','.join(row)
            mintemps = {'header': header[1:], '2009': map(float, row[1:])}

lib.show_header("CSVV:")
csvv = lib.get_csvv(csvvpath, *csvvargs)

for year in [2009, futureyear]:
    lib.show_header("Calc. of tas coefficient in %d (%f reported)" % (year, lib.excind(calcs, year-1, 'tas')))
    if use_mle:
        lib.show_coefficient_mle(csvv, preds, year, 'tas', {})
    else:
        lib.show_coefficient(csvv, preds, year, 'tas', {})

coefflist = ['tas'] + ['tas%d' % ii for ii in range(2, 5)]

lib.show_header("Calc. of minimum point temperature (%f reported)" % lib.excind(mintemps, 2009, 'analytic'))
curve = ZeroInterceptPolynomialCurve([-np.inf, np.inf], [lib.excind(calcs, 2009, coeff) for coeff in coefflist])
print ', '.join(["%f: %f" % (temp, curve(temp)) for temp in np.arange(10, 26)])

prednames = ['postas', 'postas2', 'postas3', 'postas4']

lib.show_header("Calc. of baseline (%f reported)" % (lib.excind(calcs, 2009, 'baseline')))
lines = ["bl1(weather) = sum([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, 2009, coeff) for coeff in coefflist]),
         "bl(weather) = 365 * (bl1(weather) - bl1(%.12g .^ (1:4)))" % lib.excind(mintemps, 2009, 'analytic')]
terms = []
for year in range(2001, 2011):
    terms.append("bl([%s])" % ','.join(['%.12g' % lib.excind(calcs, year, pred) for pred in prednames]))
lines.append("(" + ' + '.join(terms) + ") / 10")
lib.show_julia(lines)

lib.show_header("Calc. of result (%f reported)" % (coeffs[str(futureyear)][0]))
## Without goodmoney
lib.show_header("  Without the goodmoney assumption")
lines = ["ef1(weather) = sum([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, futureyear, coeff) for coeff in coefflist]),
         "ef(weather) = 365 * (ef1(weather) - ef1(%.12f .^ (1:4)))" % lib.excind(mintemps, 2009, 'analytic')]
lines.append("ef([%s]) - %f" % (','.join(['%.12g' % lib.excind(calcs, futureyear, pred) for pred in prednames]), lib.excind(calcs, futureyear, 'baseline')))
lib.show_julia(lines)

if use_goodmoney:
    ## Check for goodmoney problem
    lib.show_header("  Marginal effect of money")
    lines = ["gdpgammas = [%s]" % ', '.join(["%.12g" % csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['covarnames'][ii] == 'loggdppc']),
             "transpose(gdpgammas) * [%s]" % ', '.join(["%.12g" % lib.excind(calcs, futureyear, pred) for pred in prednames])]
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
             "ef1([%s]) * 100000" % ', '.join(["%.12g" % lib.excind(calcs, futureyear, pred) for pred in prednames])]
    lib.show_julia(lines)

    ## Return coefficients to baseline
    lib.show_header("  Using the goodmoney assumption")
    lines = ["gdpgammas = [%s]" % ', '.join(["%.12g" % csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['covarnames'][ii] == 'loggdppc']),
             "deltacoeff = gdpgammas .* (%.12g - %.12g)" % (lib.excind(preds, futureyear - 1, 'loggdppc'), lib.excind(preds, 2009, 'loggdppc')),
             "ef1(weather) = sum(([%s] - deltacoeff)' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, futureyear, coeff) for coeff in coefflist]),
             "ef(weather) = ef1(365 * weather) - ef1(365 * [%s])" % (', '.join(["%.12g" % term for term in np.power(lib.excind(mintemps, 2009, 'analytic'), np.arange(1, 5))])),
             "ef([%s]) - %f" % (', '.join(["%.12g" % lib.excind(calcs, futureyear, pred) for pred in prednames]), lib.excind(calcs, futureyear, 'baseline'))]
    lib.show_julia(lines)
