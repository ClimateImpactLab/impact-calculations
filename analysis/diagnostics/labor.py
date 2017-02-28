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

print "Calc of tasmax^4 predictors (1.18059e+06 reported)"
