import sys, os, csv
import numpy as np
from openest.models.curve import ZeroInterceptPolynomialCurve
import lib

futureyear = 2050
use_mle = False
use_goodmoney = True

polypower = 4

dir = sys.argv[1]
csvvpath = "/shares/gcp/social/parameters/mortality/mortality_nonFGLS_22052018/Agespec_interaction_GMFD_POLY-4_TINV_CYA_NW_w1.csvv"
weathertemplate = "/shares/gcp/climate/BCSD/hierid/popwt/daily/{variable}/{rcp}/CCSM4/{year}/1.6.nc4"
onlymodel = "Agespec_interaction_GMFD_POLY-4_TINV_CYA_NW_w1-oldest"
csvvargs = (2 * 3 * polypower, 3 * 3 * polypower) # (None, None)
region = 'USA.14.608'
onlyreg = True #False

lib.show_header("The Covariates File (allpreds):")
preds = lib.get_excerpt(os.path.join(dir, "mortality-allpreds.csv"), 3, region, [2001, 2009, futureyear-1, futureyear], onlymodel=onlymodel)

lib.show_header("The Calculations File (allcalcs):")
calcs = lib.get_excerpt(os.path.join(dir, "mortality-allcalcs-" + onlymodel + ".csv"), 2, region, range(2000, 2011) + [futureyear-1, futureyear], hasmodel=False)

lib.show_header("The Minimum Temperature Point File:")
shapenum = 0
with open(os.path.join(dir, onlymodel + "-polymins.csv"), 'r') as fp:
    reader = csv.reader(fp)
    header = reader.next()
    print ','.join(header)
    for row in reader:
        if row[0] == region:
            print ','.join(row)
            mintemps = {'header': header[1:], '2009': map(float, row[1:])}
            break
        shapenum += 1

lib.show_header("CSVV:")
csvv = lib.get_csvv(csvvpath, *csvvargs)

lib.show_header("Weather:")
lib.show_header(" tas:")
weather = lib.get_weather(weathertemplate, range(2001, 2011) + [2049, 2050, 2099], region)
lib.show_header(" tas^2:")
weather2 = lib.get_weather(weathertemplate, range(2001, 2011) + [2049, 2050, 2099], region, variable='tas-poly-2')
lib.show_header(" tas^3:")
weather3 = lib.get_weather(weathertemplate, range(2001, 2011) + [2049, 2050, 2099], region, variable='tas-poly-3')
lib.show_header(" tas^4:")
weather4 = lib.get_weather(weathertemplate, range(2001, 2011) + [2049, 2050, 2099], region, variable='tas-poly-4')

lib.show_header("Outputs:")
outputs = lib.get_outputs(os.path.join(dir, onlymodel + '.nc4'), range(2001, 2011) + [2049, 2050], shapenum if not onlyreg else 0)

for year in [2001, futureyear]:
    lib.show_header("Calc. of tas coefficient in %d (%f reported)" % (year, lib.excind(calcs, year-1, 'tas')))
    if use_mle:
        lib.show_coefficient_mle(csvv, preds, year, 'tas', {})
    else:
        lib.show_coefficient(csvv, preds, year, 'tas', {})

coefflist = ['tas'] + ['tas%d' % ii for ii in range(2, polypower + 1)]

lib.show_header("Calc. of minimum point temperature (%f reported)" % lib.excind(mintemps, 2009, 'analytic'))
curve = ZeroInterceptPolynomialCurve([-np.inf, np.inf], [lib.excind(calcs, 2000, coeff) for coeff in coefflist])
print ', '.join(["%f: %f" % (temp, curve(temp)) for temp in np.arange(10, 26)])

def get_preds(year):
    nonclipped = curve(weather[year]) > curve(lib.excind(mintemps, 2009, 'analytic'))
    return ['%.12g' % sum(weather[year][nonclipped] ** power / sum(nonclipped)) for power in range(1, polypower+1)]

lib.show_header("Calc. of baseline (%f reported)" % (lib.excind(calcs, 2000, 'baseline')))
lines = []
for year in range(2001, 2011):
    lines.append("yy_%d = %f" % (year, outputs[year]['transformed']))
lines.append("(" + ' + '.join(['yy_%d' % year for year in range(2001, 2011)]) + ") / 10")
lib.show_julia(lines)

lib.show_header("Calc. of clipped days portion (%f reported)" % lib.excind(calcs, 2050, 'zero'))
lines = ["weather_%d = [%s]" % (2050, ','.join(["%.12g" % weday for weday in weather[2050]])),
         "weather2_%d = [%s]" % (2050, ','.join(["%.12g" % weday for weday in weather2[2050]])),
         "weather3_%d = [%s]" % (2050, ','.join(["%.12g" % weday for weday in weather3[2050]])),
         "weather4_%d = [%s]" % (2050, ','.join(["%.12g" % weday for weday in weather4[2050]])),
         "eff0(weather) = ([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, 2049, coeff) for coeff in coefflist]),
         "effadj(weather, weather2, weather3, weather4) = eff0([weather'; weather2'; weather3'; weather4']) - eff0(%.12g .^ (1:%d))[1]" % (lib.excind(mintemps, 2009, 'analytic'), polypower),
         "mean(effadj(weather_%d, weather2_%d, weather3_%d, weather4_%d) .<= 0)" % (2050, 2050, 2050, 2050)]
lib.show_julia(lines)

lib.show_header("Calc. of result (%f reported)" % (outputs[futureyear]['rebased']))

lines = ["weather_%d = [%s]" % (futureyear, ','.join(["%.12g" % weday for weday in weather[futureyear]])),
         "weather2_%d = [%s]" % (futureyear, ','.join(["%.12g" % weday for weday in weather2[futureyear]])),
         "weather3_%d = [%s]" % (futureyear, ','.join(["%.12g" % weday for weday in weather3[futureyear]])),
         "weather4_%d = [%s]" % (futureyear, ','.join(["%.12g" % weday for weday in weather4[futureyear]])),
         "ucliplow(values, weather, mmt) = cummax(values[weather .< mmt][sortperm(weather[weather .< mmt], rev=true)])",
         "ucliphi(values, weather, mmt) = cummax(values[weather .>= mmt][sortperm(weather[weather .>= mmt])])",
         "uclip(values, weather, mmt) = [ucliplow(values, weather, mmt); ucliphi(values, weather, mmt)]",
         "eff0(weather) = ([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, futureyear, coeff) for coeff in coefflist]),
         "effadj(weather, weather2, weather3, weather4) = eff0([weather'; weather2'; weather3'; weather4']) - eff0(%.12g .^ (1:%d))[1]" % (lib.excind(mintemps, 2009, 'analytic'), polypower),
         "efffin(weather, weather2, weather3, weather4) = effadj(weather, weather2, weather3, weather4) .* (effadj(weather, weather2, weather3, weather4) .> 0)",
         "original = efffin(weather_%d, weather2_%d, weather3_%d, weather4_%d)" % (futureyear, futureyear, futureyear, futureyear),
         "gdpgammas = [%s]" % ', '.join(["%.12g" % csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['covarnames'][ii] == 'loggdppc']),
         "deltacoeff = gdpgammas .* (%.12g - %.12g)" % (lib.excind(preds, futureyear - 1, 'loggdppc'), lib.excind(preds, 2009, 'loggdppc')),
         "eff0(weather) = (([%s] - deltacoeff)' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, futureyear, coeff) for coeff in coefflist]),
         "effadj(weather, weather2, weather3, weather4) = eff0([weather'; weather2'; weather3'; weather4']) - eff0(%.12g .^ (1:%d))[1]" % (lib.excind(mintemps, 2009, 'analytic'), polypower),
         "efffin(weather, weather2, weather3, weather4) = effadj(weather, weather2, weather3, weather4) .* (effadj(weather, weather2, weather3, weather4) .> 0)",
         "goodmoney = efffin(weather_%d, weather2_%d, weather3_%d, weather4_%d)" % (futureyear, futureyear, futureyear, futureyear),
         "finalcurve = uclip(min(original, goodmoney), weather_%d, %.12g)" % (futureyear, lib.excind(mintemps, 2009, 'analytic')),
         "sum(finalcurve) - %.12g" % (lib.excind(calcs, 2000, 'baseline'))]
lib.show_julia(lines)

lib.show_header("Climtas effect in %d (%f reported)" % (2050, outputs[2050]['climtas_effect']))
coeffs = [csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['covarnames'][ii] == 'climtas']
lines = lines[:-1]
lines.append("culow_indexes(values, weather, mmt) = sortperm(weather[weather .< mmt], rev=true)[cummax(collect(1:sum(weather .< mmt)) + [0; diff(ucliplow(values, weather, mmt)) .== 0] .* -1000)]")
lines.append("cuhi_indexes(values, weather, mmt) = sortperm(weather[weather .>= mmt])[cummax(collect(1:sum(weather .>= mmt)) + [0; diff(ucliphi(values, weather, mmt)) .== 0] .* -1000)]")
lines.append("cu_select(xx, values, weather, mmt) = [xx[weather .< mmt][culow_indexes(values, weather, mmt)]; xx[weather .>= mmt][cuhi_indexes(values, weather, mmt)]]")
lines.append("unclipped = finalcurve .> 0")
lines.append("ceff0(weather) = ([%s]' * weather) / 100000" % ', '.join(["%.12g" % coeffs[kk] for kk in range(4)]))
lines.append("ceffadj(weather, weather2, weather3, weather4) = ceff0([weather'; weather2'; weather3'; weather4']) - ceff0(%.12g .^ (1:%d))[1]" % (lib.excind(mintemps, 2009, 'analytic'), polypower))
lines.append("100000 * sum(ceffadj(cu_select(weather_%d, min(original, goodmoney), weather_%d, %.12g), cu_select(weather2_%d, min(original, goodmoney), weather_%d, %.12g), cu_select(weather3_%d, min(original, goodmoney), weather_%d, %.12g), cu_select(weather4_%d, min(original, goodmoney), weather_%d, %.12g))' .* unclipped)" % (futureyear, futureyear, lib.excind(mintemps, 2009, 'analytic'), futureyear, futureyear, lib.excind(mintemps, 2009, 'analytic'), futureyear, futureyear, lib.excind(mintemps, 2009, 'analytic'), futureyear, futureyear, lib.excind(mintemps, 2009, 'analytic')))
lib.show_julia(lines, clipto=320)

