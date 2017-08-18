import os, sys
import lib

dir = sys.argv[1]

weathertemplate = "/shares/gcp/climate/BCSD/hierid/popwt/daily/tasmax/{0}/CCSM4/{1}/1.0.nc4"
csvvmodel = "labor_global_interaction_2factor_BEST_Poly2_15Aug"
model = "labor_global_interaction_2factor_BEST_Poly2_15Aug"
futureyear = 2050
region = 'IND.33.542.2153'
onlyreg = True #False

lib.show_header("The Covariates File (allpreds):")
preds = lib.get_excerpt(os.path.join(dir, "labor-allpreds.csv"), 3, region, [2000, futureyear-1, futureyear])

lib.show_header("The Predictors File (allcalcs):")
calcs = lib.get_excerpt(os.path.join(dir, "labor-allcalcs-%s.csv" % model), 2, region, range(2000, 2011) + [futureyear-1, futureyear], hasmodel=False)

lib.show_header("Weather:")
weather = lib.get_weather(weathertemplate, range(2001, 2011) + [2049, 2050], region, variable='tasmax')

lib.show_header("CSVV:")
csvv = lib.get_csvv("/shares/gcp/social/parameters/labor/csvvs/%s.csvv" % csvvmodel)

lib.show_header("Outputs:")
outputs = lib.get_outputs(os.path.join(dir, model + '.nc4'), [2049, 2050], region)

for year in [2000, futureyear]:
    lib.show_header("Calc of lt27-tasmax coeff in %s (%.12g reported):" % (year, lib.excind(calcs, year, 'lt27-tasmax')))
    lib.show_coefficient(csvv, preds, year, 'tasmax', {'hotdd_30*(tasmax - 27)*I_{T >= 27}': None, 'colddd_10*(27 - tasmax)*I_{T < 27}': 'colddd_10'})

    lib.show_header("Calc of gt27-tasmax coeff in %s (%.12g reported):" % (year, lib.excind(calcs, year, 'gt27-tasmax')))
    lib.show_coefficient(csvv, preds, year, 'tasmax', {'hotdd_30*(tasmax - 27)*I_{T >= 27}': 'hotdd_30', 'colddd_10*(27 - tasmax)*I_{T < 27}': None})

lib.show_header("Calc of baseline (%.12g reported):" % lib.excind(calcs, 2000, 'baseline'))
coeff = ['tasmax', 'tasmax2']
gt27_covars = ['hotdd_30*(tasmax - 27)*I_{T >= 27}', 'hotdd_30*(tasmax2 - 27^2)*I_{T >= 27}']
lt27_covars = ['colddd_10*(27 - tasmax)*I_{T < 27}', 'colddd_10*(27^2 - tasmax2)*I_{T < 27}']
var = ['t1', 't2']

lines_weather = []
for year in range(2001, 2011):
    lines_weather.append("weather_%d = [%s]" % (year, ','.join(["%.12g" % weday for weday in weather[year]])))

lines = []
lines.append("f_lt27(t1, t2, tz) = " + ' + '.join(["%.12g * %s - %f * 27^%d * %f" % (lib.excind(calcs, 2000, 'lt27-' + coeff[ii]), var[ii], lib.get_gamma(csvv, coeff[ii], lt27_covars[ii]), ii+1, lib.excind(preds, 2000, 'colddd_10')) for ii in range(2)]))
lines.append("f_gt27(t1, t2, tz) = " + ' + '.join(["%.12g * %s - %f * 27^%d * %f" % (lib.excind(calcs, 2000, 'gt27-' + coeff[ii]), var[ii], lib.get_gamma(csvv, coeff[ii], gt27_covars[ii]), ii+1, lib.excind(preds, 2000, 'hotdd_30')) for ii in range(2)]))
lines.append("f_both(t1, t2, tz) = f_lt27(t1, t2, tz) .* (t1 .< 27) + f_gt27(t1, t2, tz) .* (t1 .>= 27)")
lines.append("f(t1, t2, tz) = sum(f_both(t1, t2, tz) - f_both(27, 27^2, 0)) / 365")

line_base = '(' + ' + '.join(["f(weather_%d, weather_%d.^2, 0)" % (year, year) for year in range(2001, 2011)]) + ') / 10'
lib.show_julia(lines_weather + lines + [line_base])

lib.show_header("Calc. of result (%.12g reported)" % (outputs[2050]['rebased']))

line_weather = "weather_%d = [%s]" % (futureyear, ','.join(["%.12g" % weday for weday in weather[futureyear]]))

lines = []    
lines.append("f_lt27(t1, t2, tz) = " + ' + '.join(["%.12g * %s - %f * 27^%d * %f" % (lib.excind(calcs, futureyear-1, 'lt27-' + coeff[ii]), var[ii], lib.get_gamma(csvv, coeff[ii], lt27_covars[ii]), ii+1, lib.excind(preds, futureyear-1, 'colddd_10')) for ii in range(2)]))
lines.append("f_gt27(t1, t2, tz) = " + ' + '.join(["%.12g * %s - %f * 27^%d * %f" % (lib.excind(calcs, futureyear-1, 'gt27-' + coeff[ii]), var[ii], lib.get_gamma(csvv, coeff[ii], gt27_covars[ii]), ii+1, lib.excind(preds, futureyear-1, 'hotdd_30')) for ii in range(2)]))
lines.append("f_both(t1, t2, tz) = f_lt27(t1, t2, tz) .* (t1 .< 27) + f_gt27(t1, t2, tz) .* (t1 .>= 27)")
lines.append("f(t1, t2, tz) = sum(f_both(t1, t2, tz) - f_both(27, 27^2, 0)) / 365")

line_result = "f(weather_%d, weather_%d.^2, 0) - %.12g" % (futureyear, futureyear, lib.excind(calcs, 2050, 'baseline'))
lib.show_julia([line_weather] + lines + [line_result])
