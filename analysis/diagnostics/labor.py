import os, sys
import lib

dir = sys.argv[1]

lib.show_header("The Covariates File (allpreds):")
preds = lib.get_excerpt(os.path.join(dir, "labor-allpreds.csv"), 3, 'IND.33.542.2153', [2009, 2049, 2050])

lib.show_header("The Coefficients File (allcoeffs):")
coeffs = lib.get_excerpt(os.path.join(dir, "labor-allcoeffs.csv"), 3, 'IND.33.542.2153', [2009, 2049, 2050])

lib.show_header("The Predictors File (allcalcs):")
calcs = lib.get_excerpt(os.path.join(dir, "labor-allcalcs-labor_global_interaction_2factor_BEST_14feb.csv"), 2, 'IND.33.542.2153', range(2001, 2011) + [2050], hasmodel=False)

lib.show_header("CSVV:")
csvv = lib.get_csvv("/shares/gcp/social/parameters/labor/labor_global_interaction_2factor_BEST_14feb.csvv")

lib.show_header("Calc of tasmax^4 predictors (%f reported):" % lib.excind(calcs, 2005, 'avgtk_4'))
lib.show_julia("%f^4" % lib.excind(calcs, 2005, 'avgtk_1'))

for year in [2009, 2050]:
    lib.show_header("Calc of tasmax coeff in %s (%.12g reported):" % (year, lib.excind(coeffs, year, 'tasmax')))
    lib.show_coefficient(csvv, preds, year, 'tasmax', {})

lib.show_header("Calc of baseline (%.12g reported):" % lib.excind(calcs, 2009, 'baseline'))
coeff = ['tasmax', 'tasmax2', 'tasmax3', 'tasmax4']
var = ['t1', 't2', 't3', 't4']
line1 = "bl1(t1, t2, t3, t4, tz) = " + ' + '.join(["%.12g * %s" % (lib.excind(coeffs, 2009, coeff[ii]), var[ii]) for ii in range(4)])
line2 = "bl(t1, t2, t3, t4, tz) = bl1(t1, t2, t3, t4, tz) - bl1(27, 27^2, 27^3, 27^4, 0)"
line3 = '(' + ' + '.join(["bl(%.12g, %.12g, %.12g, %.12g, 0)" % (lib.excind(calcs, year, 'avgtk_1'), lib.excind(calcs, year, 'avgtk_2'), lib.excind(calcs, year, 'avgtk_3'), lib.excind(calcs, year, 'avgtk_4')) for year in range(2001, 2011)]) + ') / 10'
lib.show_julia([line1, line2, line3])

lib.show_header("Calc. of result (%.12g reported)" % (coeffs['2050'][0]))
line1 = "ef1(t1, t2, t3, t4, tz) = " + ' + '.join(["%.12g * %s" % (lib.excind(coeffs, 2049, coeff[ii]), var[ii]) for ii in range(4)])
line2 = "ef(t1, t2, t3, t4, tz) = ef1(t1, t2, t3, t4, tz) - ef1(27, 27^2, 27^3, 27^4, 0)"
line3 = "ef(%.12g, %.12g, %.12g, %.12g, 0) - %.12g" % (lib.excind(calcs, 2050, 'avgtk_1'), lib.excind(calcs, 2050, 'avgtk_2'), lib.excind(calcs, 2050, 'avgtk_3'), lib.excind(calcs, 2050, 'avgtk_4'), lib.excind(calcs, 2050, 'baseline'))
lib.show_julia([line1, line2, line3])
