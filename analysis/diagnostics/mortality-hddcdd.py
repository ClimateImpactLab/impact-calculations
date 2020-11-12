import sys, os
import lib

futureyear = 2050

terms = 2
variables = ["tas-10-spline-poly-2", "tas-25-spline-poly-2"]
coeffnames = ['hdd10', 'cdd25']

outdir = sys.argv[1]
csvvpath = "/shares/gcp/social/parameters/mortality/polyspline_dd/quadratic/Agespec_interaction_response_polyspline_10C_25C_order2_GMFD.csvv"
weathertemplate = "/shares/gcp/climate/BCSD/hierid/popwt/annual/{variable}/{rcp}/CCSM4/{year}/1.0.nc4"
onlymodel = "Agespec_interaction_response_polyspline_10C_25C_order2_GMFD-oldest"
csvvargs = (2 * 3 * terms, 3 * 3 * terms) # (None, None)
region = 'USA.14.608'
onlyreg = True #False

lib.show_header("The Covariates File (allpreds):")
preds = lib.get_excerpt(os.path.join(outdir, "mortality-allpreds.csv"), 3, region, [2001, 2009, futureyear-1, futureyear], onlymodel=onlymodel)

lib.show_header("The Calculations File (allcalcs):")
calcs = lib.get_excerpt(os.path.join(outdir, "mortality-allcalcs-" + onlymodel + ".csv"), 2, region, list(range(2000, 2011)) + [futureyear-1, futureyear], hasmodel=False)

lib.show_header("CSVV:")
csvv = lib.get_csvv(csvvpath, *csvvargs)

lib.show_header("Weather:")
weathers = {}
for variable in variables:
    lib.show_header(" %s:" % variable)
    weathers[variable] = lib.get_weather(weathertemplate, list(range(2001, 2011)) + [2049, 2050, 2099], region, variable=variable)

lib.show_header("Outputs:")
outputs = lib.get_outputs(os.path.join(outdir, onlymodel + '.nc4'), list(range(2001, 2011)) + [2049, 2050], 0)

lib.show_header("Calc. of baseline (%f reported)" % (lib.excind(calcs, 2000, 'baseline')))
lines = []
for year in range(2001, 2011):
    lines.append("yy_%d = %f" % (year, outputs[year]['transformed']))
lines.append("(" + ' + '.join(['yy_%d' % year for year in range(2001, 2011)]) + ") / 10")
lib.show_julia(lines)

lib.show_header("Calc. of result (%f reported)" % (outputs[futureyear]['rebased']))

lines = []
for variable in variables:
    lines.append("%s_%d = %.12g" % (variable.replace('-', '_'), futureyear, weathers[variable][futureyear]))
for coeffname in coeffnames:
    lines.append("%s_%d = %s" % (coeffname, futureyear, lib.show_coefficient(csvv, preds, futureyear, coeffname, {}, calconly=True)))
    lines.append("%s_inc0 = %s" % (coeffname, lib.show_coefficient(csvv, preds, 2009, coeffname, {}, calconly=True)))

lib.show_header("  Without good-money:")
mylines = list(lines)
    
mylines.append("effect(weather) = ([%s]' * weather) / 100000" % ', '.join(["max(0, %s_%d)" % (coeffname, futureyear) for coeffname in coeffnames]))
mylines.append("effect([%s]) - %.12g" % (', '.join(["%s_%d" % (variable.replace('-', '_'), futureyear) for variable in variables]), lib.excind(calcs, 2000, 'baseline')))
lib.show_julia(mylines)

lib.show_header("  With good-money:")
mylines = list(lines)
    
mylines.append("effect(weather) = ([%s]' * weather) / 100000" % ', '.join(["min(max(0, %s_%d), max(0, %s_inc0))" % (coeffname, futureyear, coeffname) for coeffname in coeffnames]))
mylines.append("effect([%s]) - %.12g" % (', '.join(["%s_%d" % (variable.replace('-', '_'), futureyear) for variable in variables]), lib.excind(calcs, 2000, 'baseline')))
lib.show_julia(mylines)
