import os, sys
import lib

dir = sys.argv[1]

weathertemplate = "/shares/gcp/climate/BCSD/hierid/popwt/daily/tasmax/{0}/CCSM4/{1}/1.0.nc4"
csvvmodel = "labor_global_interaction_2factor_BEST_Poly3_15Aug"
model = "labor_global_interaction_2factor_BEST_Poly3_15Aug"
futureyear = 2050
region = 'USA.14.608' #'IND.33.542.2153'
onlyreg = True #False

lib.show_header("The Covariates File (allpreds):")
preds = lib.get_excerpt(os.path.join(dir, "labor-allpreds.csv"), 3, region, [2000, futureyear-1, futureyear])

lib.show_header("The Predictors File (allcalcs):")
calcs = lib.get_excerpt(os.path.join(dir, "labor-allcalcs-%s.csv" % model), 2, region, list(range(2000, 2011)) + [futureyear-1, futureyear], hasmodel=False)

lib.show_header("Weather:")
weather = lib.get_weather(weathertemplate, [1981] + list(range(2001, 2011)) + [futureyear-1, futureyear], region, variable='tasmax')

lib.show_header("CSVV:")
csvv = lib.get_csvv("/shares/gcp/social/parameters/labor/csvvs/%s.csvv" % csvvmodel)

lib.show_header("Outputs:")
outputs = lib.get_outputs(os.path.join(dir, model + '.nc4'), [1981, futureyear-1, futureyear], region)

for year in [2000, futureyear]:
    lib.show_header("Calc of lt27-tasmax coeff in %s (%.12g reported):" % (year, lib.excind(calcs, year, 'lt27-tasmax')))
    lib.show_coefficient(csvv, preds, year, 'tasmax', {'hotdd_30*(tasmax - 27)*I_{T >= 27}': None, 'colddd_10*(27 - tasmax)*I_{T < 27}': 'colddd_10'})

    lib.show_header("Calc of gt27-tasmax coeff in %s (%.12g reported):" % (year, lib.excind(calcs, year, 'gt27-tasmax')))
    lib.show_coefficient(csvv, preds, year, 'tasmax', {'hotdd_30*(tasmax - 27)*I_{T >= 27}': 'hotdd_30', 'colddd_10*(27 - tasmax)*I_{T < 27}': None})

lib.show_header("Un-rebased value in 1981 (%.12g reported):" % outputs[1981]['sum'])
coeff = ['tasmax', 'tasmax2', 'tasmax3']
gt27_covars = ['hotdd_30*(tasmax - 27)*I_{T >= 27}', 'hotdd_30*(tasmax2 - 27^2)*I_{T >= 27}', 'hotdd_30*(tasmax3 - 27^3)*I_{T >= 27}']
lt27_covars = ['colddd_10*(27 - tasmax)*I_{T < 27}', 'colddd_10*(27^2 - tasmax2)*I_{T < 27}', 'colddd_10*(27^3 - tasmax3)*I_{T < 27}']
var = ['t1', 't2', 't3']

line_weather = "weather_%d = [%s]" % (1981, ','.join(["%.12g" % weday for weday in weather[1981]]))

lines = []    
lines.append("f_lt27(t1, t2, t3) = " + ' + '.join(["%.12g * %s - %f * 27^%d * %f" % (lib.excind(calcs, 2000, 'lt27-' + coeff[ii]), var[ii], lib.get_gamma(csvv, coeff[ii], lt27_covars[ii]), ii+1, lib.excind(preds, 2000, 'colddd_10')) for ii in range(3)]))
lines.append("f_gt27(t1, t2, t3) = " + ' + '.join(["%.12g * %s - %f * 27^%d * %f" % (lib.excind(calcs, 2000, 'gt27-' + coeff[ii]), var[ii], lib.get_gamma(csvv, coeff[ii], gt27_covars[ii]), ii+1, lib.excind(preds, 2000, 'hotdd_30')) for ii in range(3)]))
lines.append("f_both(t1, t2, t3) = f_lt27(t1, t2, t3) .* (t1 .< 27) + f_gt27(t1, t2, t3) .* (t1 .>= 27)")
lines.append("f(t1, t2, t3) = sum((t1 .>= 0) .* (f_both(t1, t2, t3) - f_both(27, 27^2, 27^3)) + (t1 .< 0) .* %f) / 365" % lib.get_gamma(csvv, 'belowzero', '1'))

line_result = "f(weather_%d, weather_%d.^2, weather_%d.^3)" % (1981, 1981, 1981)
lib.show_julia([line_weather] + lines + [line_result], clipto=200)


lib.show_header("Calc of baseline (%.12g reported):" % lib.excind(calcs, 2000, 'baseline'))

lines_weather = []
for year in range(2001, 2011):
    lines_weather.append("weather_%d = [%s]" % (year, ','.join(["%.12g" % weday for weday in weather[year]])))

lines = []
lines.append("f_lt27(t1, t2, t3) = " + ' + '.join(["%.12g * %s - %f * 27^%d * %f" % (lib.excind(calcs, 2000, 'lt27-' + coeff[ii]), var[ii], lib.get_gamma(csvv, coeff[ii], lt27_covars[ii]), ii+1, lib.excind(preds, 2000, 'colddd_10')) for ii in range(3)]))
lines.append("f_gt27(t1, t2, t3) = " + ' + '.join(["%.12g * %s - %f * 27^%d * %f" % (lib.excind(calcs, 2000, 'gt27-' + coeff[ii]), var[ii], lib.get_gamma(csvv, coeff[ii], gt27_covars[ii]), ii+1, lib.excind(preds, 2000, 'hotdd_30')) for ii in range(3)]))
lines.append("f_both(t1, t2, t3) = f_lt27(t1, t2, t3) .* (t1 .< 27) + f_gt27(t1, t2, t3) .* (t1 .>= 27)")
lines.append("f(t1, t2, t3) = sum((t1 .>= 0) .* (f_both(t1, t2, t3) - f_both(27, 27^2, 27^3)) + (t1 .< 0) .* %f) / 365" % lib.get_gamma(csvv, 'belowzero', '1'))

line_base = '(' + ' + '.join(["f(weather_%d, weather_%d.^2, weather_%d.^3)" % (year, year, year) for year in range(2001, 2011)]) + ') / 10'
lib.show_julia(lines_weather + lines + [line_base], clipto=200)

lib.show_header("Calc. of result (%.12g reported)" % (outputs[futureyear]['rebased']))

line_weather = "weather_%d = [%s]" % (futureyear, ','.join(["%.12g" % weday for weday in weather[futureyear]]))

lines = []    
lines.append("f_lt27(t1, t2, t3) = " + ' + '.join(["%.12g * %s - %f * 27^%d * %f" % (lib.excind(calcs, futureyear-1, 'lt27-' + coeff[ii]), var[ii], lib.get_gamma(csvv, coeff[ii], lt27_covars[ii]), ii+1, lib.excind(preds, futureyear-1, 'colddd_10')) for ii in range(3)]))
lines.append("f_gt27(t1, t2, t3) = " + ' + '.join(["%.12g * %s - %f * 27^%d * %f" % (lib.excind(calcs, futureyear-1, 'gt27-' + coeff[ii]), var[ii], lib.get_gamma(csvv, coeff[ii], gt27_covars[ii]), ii+1, lib.excind(preds, futureyear-1, 'hotdd_30')) for ii in range(3)]))
lines.append("f_both(t1, t2, t3) = f_lt27(t1, t2, t3) .* (t1 .< 27) + f_gt27(t1, t2, t3) .* (t1 .>= 27)")
lines.append("f(t1, t2, t3) = sum((t1 .>= 0) .* (f_both(t1, t2, t3) - f_both(27, 27^2, 27^3)) + (t1 .< 0) .* %f) / 365" % lib.get_gamma(csvv, 'belowzero', '1'))

line_result = "f(weather_%d, weather_%d.^2, weather_%d.^3) - %.12g" % (futureyear, futureyear, futureyear, lib.excind(calcs, futureyear, 'baseline'))
lib.show_julia([line_weather] + lines + [line_result], clipto=200)
