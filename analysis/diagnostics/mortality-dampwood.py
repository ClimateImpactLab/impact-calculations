import sys, os, csv
import numpy as np
from openest.models.curve import CubicSplineCurve
import lib

futureyear = 2050
use_mle = True
use_goodmoney = False

dir = sys.argv[1]
csvvdir = "/shares/gcp/social/parameters/mortality/MLE_splines_03212017/"
onlymodel = "MLE_splines_GMFD_03212017" #"moratlity_cubic_splines_2factors_BEST_031617"

lib.show_header("The Covariates File (allpreds):")
preds = lib.get_excerpt(os.path.join(dir, "mortality-allpreds.csv"), 3, 'IND.33.542.2153', [2009, futureyear-1, futureyear], onlymodel=onlymodel)

lib.show_header("The Coefficients File (allcoeffs):")
coeffs = lib.get_excerpt(os.path.join(dir, "mortality-allcoeffs.csv"), 3, 'IND.33.542.2153', [2009, futureyear-1, futureyear], onlymodel=onlymodel)

lib.show_header("The Predictors File (allcalcs):")
calcs = lib.get_excerpt(os.path.join(dir, "mortality-allcalcs-" + onlymodel + ".csv"), 2, 'IND.33.542.2153', range(2001, 2011) + [futureyear], hasmodel=False)

lib.show_header("The Minimum Temperature Point File:")
with open(os.path.join(dir, onlymodel + "-splinemins.csv"), 'r') as fp:
    reader = csv.reader(fp)
    header = reader.next()
    print ','.join(header)
    for row in reader:
        if row[0] == 'IND.33.542.2153':
            print ','.join(row)
            mintemps = {'header': header[1:], '2009': map(float, row[1:])}

lib.show_header("CSVV:")
csvv = lib.get_csvv(os.path.join(csvvdir, onlymodel + ".csvv"))

lib.show_header("Calculation of spline terms for tas_sum = %f, assuming constant days (%s reported)" % (lib.excind(calcs, 2009, 'var-0'), ', '.join(["%.12g" % lib.excind(calcs, 2009, 'var-%d' % ii) for ii in range(1, 7)])))
curve = CubicSplineCurve([-12, -7, 0, 10, 18, 23, 28, 33], None)
print "# " + ', '.join(map(str, 365 * np.array(curve.get_terms(lib.excind(calcs, 2009, 'var-0') / 365))))

for year in [2009, futureyear]:
    lib.show_header("Calc. of tas_sum coefficient in %d (%f reported)" % (year, lib.excind(coeffs, year, 'tas_sum')))
    if use_mle:
        lib.show_coefficient_mle(csvv, preds, year, 'spline_variables-0', {})
    else:
        lib.show_coefficient(csvv, preds, year, 'spline_variables-0', {})

coefflist = ['tas_sum'] + ['spline_variables-%d' % ii for ii in range(1, 7)]

lib.show_header("Calc. of minimum point temperature (%f reported)" % lib.excind(mintemps, 2009, 'analytic'))
curve = CubicSplineCurve([-12, -7, 0, 10, 18, 23, 28, 33], [lib.excind(coeffs, 2009, coeff) for coeff in coefflist])
print ', '.join(["%f: %f" % (temp, curve(temp)) for temp in np.arange(10, 26)])

lib.show_header("Calc. of baseline (%f reported)" % (lib.excind(calcs, 2009, 'baseline')))
lines = ["bl1(weather) = sum([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(coeffs, 2009, coeff) for coeff in coefflist]),
         "bl(weather) = bl1(weather) - bl1(365 * [%s])" % (', '.join(["%d" % term for term in curve.get_terms(lib.excind(mintemps, 2009, 'analytic'))]))]
terms = []
for year in range(2001, 2011):
    terms.append("bl([%s])" % ', '.join(["%.12g" % lib.excind(calcs, year, 'var-%d' % ii) for ii in range(7)]))
lines.append("(" + ' + '.join(terms) + ") / 10")
lib.show_julia(lines)

lib.show_header("Calc. of result (%f reported)" % (coeffs[str(futureyear)][0]))
## Without goodmoney
lib.show_header("  Without the goodmoney assumption")
lines = ["ef1(weather) = sum([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(coeffs, futureyear, coeff) for coeff in coefflist]),
        "ef(weather) = ef1(weather) - ef1(365 * [%s])" % (', '.join(["%d" % term for term in curve.get_terms(lib.excind(mintemps, 2009, 'analytic'))]))]
lines.append("ef([%s]) - %f" % (', '.join(["%.12g" % lib.excind(calcs, futureyear, 'var-%d' % ii) for ii in range(7)]), lib.excind(calcs, futureyear, 'baseline')))
lib.show_julia(lines)

if use_goodmoney:
    ## Check for goodmoney problem
    lib.show_header("  Marginal effect of money")
    lines = ["gdpgammas = [%s]" % ', '.join(["%.12g" % csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['covarnames'][ii] == 'loggdppc']),
             "transpose(gdpgammas) * [%s]" % ', '.join(["%.12g" % lib.excind(calcs, futureyear, 'var-%d' % ii) for ii in range(7)])]
    lib.show_julia(lines)

    # ## What are the new coefficients
    # lines = ["gdpgammas = [%s]" % ', '.join(["%.12g" % csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['covarnames'][ii] == 'loggdppc']),
    #          "deltacoeff = gdpgammas .* (%.12g - %.12g)" % (lib.excind(preds, futureyear - 1, 'loggdppc'), lib.excind(preds, 2009, 'loggdppc')),
    #          "[%s] - deltacoeff" % ', '.join(["%.12g" % lib.excind(coeffs, futureyear, coeff) for coeff in coefflist])]
    # lib.show_julia(lines)

    # ## Check components
    # lines = ["gdpgammas = [%s]" % ', '.join(["%.12g" % csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['covarnames'][ii] == 'loggdppc']),
    #          "deltacoeff = gdpgammas .* (%.12g - %.12g)" % (lib.excind(preds, futureyear - 1, 'loggdppc'), lib.excind(preds, 2009, 'loggdppc')),
    #          "ef1(weather) = sum(([%s] - deltacoeff)' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(coeffs, futureyear, coeff) for coeff in coefflist]),
    #          "ef1([%s]) * 100000" % ', '.join(["%.12g" % lib.excind(calcs, futureyear, 'var-%d' % ii) for ii in range(7)])]
    # lib.show_julia(lines)

    # lines = ["gdpgammas = [%s]" % ', '.join(["%.12g" % csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['covarnames'][ii] == 'loggdppc']),
    #          "deltacoeff = gdpgammas .* (%.12g - %.12g)" % (lib.excind(preds, futureyear - 1, 'loggdppc'), lib.excind(preds, 2009, 'loggdppc')),
    #          "ef1(weather) = sum(([%s] - deltacoeff)' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(coeffs, futureyear, coeff) for coeff in coefflist]),
    #          "ef1(365 * [%s]) * 100000" % (', '.join(["%d" % term for term in curve.get_terms(lib.excind(mintemps, 2009, 'analytic'))]))]
    # lib.show_julia(lines)

    ## Return coefficients to baseline
    lib.show_header("  Using the goodmoney assumption")
    lines = ["gdpgammas = [%s]" % ', '.join(["%.12g" % csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['covarnames'][ii] == 'loggdppc']),
             "deltacoeff = gdpgammas .* (%.12g - %.12g)" % (lib.excind(preds, futureyear - 1, 'loggdppc'), lib.excind(preds, 2009, 'loggdppc')),
             "ef1(weather) = sum(([%s] - deltacoeff)' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(coeffs, futureyear, coeff) for coeff in coefflist]),
             "ef(weather) = ef1(weather) - ef1(365 * [%s])" % (', '.join(["%d" % term for term in curve.get_terms(lib.excind(mintemps, 2009, 'analytic'))])),
             "ef([%s]) - %f" % (', '.join(["%.12g" % lib.excind(calcs, futureyear, 'var-%d' % ii) for ii in range(7)]), lib.excind(calcs, futureyear, 'baseline'))]
    lib.show_julia(lines)
