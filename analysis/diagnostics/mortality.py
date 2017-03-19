import sys, os, csv
from netCDF4 import Dataset
import numpy as np
from openest.models.curve import CubicSplineCurve
import lib

dir = sys.argv[1]
onlymodel = "moratlity_cubic_splines_2factors_BEST_031617"

lib.show_header("The Covariates File (allpreds):")
preds = lib.get_excerpt(os.path.join(dir, "mortality-allpreds.csv"), 3, 'IND.33.542.2153', [2009, 2049, 2050], onlymodel=onlymodel)

lib.show_header("The Coefficients File (allcoeffs):")
coeffs = lib.get_excerpt(os.path.join(dir, "mortality-allcoeffs.csv"), 3, 'IND.33.542.2153', [2009, 2049, 2050], onlymodel=onlymodel)

lib.show_header("The Predictors File (allcalcs):")
calcs = lib.get_excerpt(os.path.join(dir, "mortality-allcalcs-" + onlymodel + ".csv"), 2, 'IND.33.542.2153', range(2001, 2011) + [2050], hasmodel=False)

lib.show_header("CSVV:")
csvv = lib.get_csvv("/shares/gcp/social/parameters/mortality/cubic_splines/" + onlymodel + ".csvv")

lib.show_header("Calculation of spline terms for tas_sum = %f, assuming constant days (%s reported)" % (lib.excind(calcs, 2009, 'var-0'), ', '.join(["%.12g" % lib.excind(calcs, 2009, 'var-%d' % ii) for ii in range(1, 7)])))
curve = CubicSplineCurve([-12, -7, 0, 10, 18, 23, 28, 33], None)
print "# " + ', '.join(map(str, 365 * np.array(curve.get_terms(lib.excind(calcs, 2009, 'var-0') / 365))))

for year in [2009, 2050]:
    lib.show_header("Calc. of tas_sum coefficient in %d (%f reported)" % (year, lib.excind(coeffs, year, 'tas_sum')))
    lib.show_coefficient(csvv, preds, year, 'spline_variables-0', {})

coefflist = ['tas_sum'] + ['spline_variables-%d' % ii for ii in range(1, 7)]

lib.show_header("Calc. of minimum point temperature (%f reported)", % lib.excind(calcs, 2009, 'mintemp'))
curve = CubicSplineCurve([-12, -7, 0, 10, 18, 23, 28, 33], [lib.excind(coeffs, 2009, coeff) for coeff in coefflist])
print curve(np.arange(10, 26))

lib.show_header("Calc. of baseline (%f reported)" % (lib.excind(calcs, 2009, 'baseline')))
lines = ["bl1(weather) = sum([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(coeffs, 2009, coeff) for coeff in coefflist]),
         "bl(weather) = bl1(weather) - bl1(365 * [%s])" % (', '.join(["%d" % lib.excind(curve.get_terms(lib.excind(calcs, 2009, 'mintemp')))]))]
terms = []
for year in range(2001, 2011):
    terms.append("bl([%s])" % ', '.join(["%.12g" % lib.excind(calcs, year, 'var-%d' % ii) for ii in range(7)]))
lines.append("(" + ' + '.join(terms) + ") / 10")
lib.show_julia(lines)

lib.show_header("Calc. of result (%f reported)" % (coeffs['2050'][0]))
lines = ["ef1(weather) = sum([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(coeffs, 2050, coeff) for coeff in coefflist]),
         "ef(weather) = ef1(weather) - ef1(365 * [%s])" % (', '.join(["%d" % lib.excind(curve.get_terms(lib.excind(calcs, 2009, 'mintemp')))]))]
lines.append("ef([%s]) - %f" % (', '.join(["%.12g" % lib.excind(calcs, 2050, 'var-%d' % ii) for ii in range(7)]), lib.excind(calcs, 2050, 'baseline')))
lib.show_julia(lines)
