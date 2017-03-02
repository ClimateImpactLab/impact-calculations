import os
import lib

print "\nThe Covariates File (allpreds):"
preds = lib.get_excerpt(os.path.join(dir, "labor-allpreds.csv"), 3, 'IND.33.542.2153', [2005, 2049, 2050])

print "\nThe Coefficients File (allcoeffs):"
bins = lib.get_excerpt(os.path.join(dir, "labor-allcoeffs.csv"), 3, 'IND.33.542.2153', [2005, 2049, 2050])

print "\nThe Predictors File (allcalcs):"
calcs = lib.get_excerpt(os.path.join(dir, "labor-allcalcs.csv"), 2, 'IND.33.542.2153', range(2001, 2011) + [2050])

print "\nCSVV:"
csvv = lib.get_csvv("/shares/gcp/social/parameters/labor/labor_global_interaction_2factor_BEST_14feb.csvv")

print "Calc of tasmax^4 predictors (%f reported):" % excind(calcs, 2005, 'avgtk_4')
show_julia("%f^4" % excind(calcs, 2005, 'avgtk_1'))

for year in [2005, 2050]:
    print "Calc of tasmax coeff in %s (%f reported):" % (year, excind(bins, year, 'tasmax'))
    lib.show_coefficient(year, 'tasmax', {})

print "Calc of baseline (%f reported):" % excind(calcs, 2005, 'basename')
coeff = ['tasmax', 'tasmax2', 'tasmax3', 'tasmax4']
var = ['t1', 't2', 't3', 't4']
line1 = "bl1(t1, t2, t3, t4, tz) = " + ' + '.join(["%f * %s" % (excind(coeffs, 2005, coeff[ii]), var[ii]) for ii in range(4)])
line2 = "bl(t1, t2, t3, t4, tz) = bl1(t1, t2, t3, t4, tz) - bl1(27, 27^2, 27^3, 27^4, 0)"
line3 = '(' + ' + '.join(["bl(%f, %f, %f, %f, 0)" % (excind(calcs, year, 'avgtk_1'), excind(calcs, year, 'avgtk_2'), excind(calcs, year, 'avgtk_3'), excind(calcs, year, 'avgtk_4')) for year in range(2001, 2011)]) + ') / 10'
lib.show_julia([line1, line2, line3])

print "Calc. of result (%f reported)" % (coeffs['2050'][0])
line1 = "ef1(t1, t2, t3, t4, tz) = " + + ' + '.join(["%f * %s" % (excind(coeffs, 2049, coeff[ii]), var[ii]) for ii in range(4)])
line2 = "ef(t1, t2, t3, t4, tz) = ef1(t1, t2, t3, t4, tz) - ef1(27, 27^2, 27^3, 27^4, 0)"
line3 = "bl(%f, %f, %f, %f, 0) - %f" % (excind(calcs, 2050, 'avgtk_1'), excind(calcs, 2050, 'avgtk_2'), excind(calcs, 2050, 'avgtk_3'), excind(calcs, 2050, 'avgtk_4'), escind(calcs, 2050, 'baseline'))
lib.show_julia([line1, line2, line3])
