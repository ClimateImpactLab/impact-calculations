import sys, os, csv
import numpy as np
from openest.models.curve import ZeroInterceptPolynomialCurve
import lib

futureyear = 2050
use_mle = False
use_goodmoney = True

polypower = 4

dir = sys.argv[1]
csvvpath = "/shares/gcp/social/parameters/mortality/Diagnostics_Apr17/global_interaction_Tmean-POLY-%d-AgeSpec.csvv" % polypower
weathertemplate = "/shares/gcp/climate/BCSD/aggregation/cmip5/IR_level/{0}/CCSM4/tas/tas_day_aggregated_{0}_r1i1p1_CCSM4_{1}.nc"
onlymodel = "global_interaction_Tmean-POLY-%d-AgeSpec-young" % polypower
csvvargs = (0, 3 * polypower) # (None, None)
region = 'IND.33.542.2153'
onlyreg = False
skip_clipping = True #False
module = 'lincom' #'mortality'

lib.show_header("The Covariates File (allpreds):")
preds = lib.get_excerpt(os.path.join(dir, module + "-allpreds.csv"), 3, region, [2001, 2009, futureyear-1, futureyear], onlymodel=onlymodel)

lib.show_header("The Result File (allcoeffs):")
outputs = lib.get_outputs(os.path.join(dir, onlymodel + ".nc4"), [2009, futureyear-1, futureyear], region)

lib.show_header("The Predictors File (allcalcs):")
calcs = lib.get_excerpt(os.path.join(dir, module + "-allcalcs-" + onlymodel + ".csv"), 2, region, list(range(2000, 2011)) + [futureyear-1, futureyear], hasmodel=False)

if not skip_clipping:
    lib.show_header("The Minimum Temperature Point File:")
    shapenum = 0
    with open(os.path.join(dir, onlymodel + "-polymins.csv"), 'r') as fp:
        reader = csv.reader(fp)
        header = next(reader)
        print((','.join(header)))
        for row in reader:
            if row[0] == region:
                print((','.join(row)))
                mintemps = {'header': header[1:], '2009': list(map(float, row[1:]))}
                break
            shapenum += 1
else:
    shapenum = 0
    with open(os.path.join("/shares/gcp/regions/hierarchy-flat.csv"), 'r') as fp:
        reader = csv.reader(fp)
        header = next(reader)
        for row in reader:
            if row[0] == region:
                shapenum = int(row[header.index('agglomid')]) - 1
                break
        
lib.show_header("CSVV:")
csvv = lib.get_csvv(csvvpath, *csvvargs)

lib.show_header("Weather:")
weather = lib.get_weather(weathertemplate, list(range(2001, 2011)) + [2049, 2050], shapenum)

lib.show_header("Outputs:")
outputs = lib.get_outputs(os.path.join(dir, onlymodel + '.nc4'), [2049, 2050], shapenum if not onlyreg else 0)

for year in [2001, futureyear]:
    lib.show_header("Calc. of tas coefficient in %d (%f reported)" % (year, lib.excind(calcs, year-1, 'tas')))
    if use_mle:
        lib.show_coefficient_mle(csvv, preds, year, 'tas', {})
    else:
        lib.show_coefficient(csvv, preds, year, 'tas', {})

coefflist = ['tas'] + ['tas%d' % ii for ii in range(2, polypower + 1)]

if not skip_clipping:
    lib.show_header("Calc. of minimum point temperature (%f reported)" % lib.excind(mintemps, 2009, 'analytic'))
    curve = ZeroInterceptPolynomialCurve([-np.inf, np.inf], [lib.excind(calcs, 2000, coeff) for coeff in coefflist])
    print((', '.join(["%f: %f" % (temp, curve(temp)) for temp in np.arange(10, 26)])))

def get_preds(year):
    nonclipped = curve(weather[year]) > curve(lib.excind(mintemps, 2009, 'analytic'))
    return ['%.12g' % sum(weather[year][nonclipped] ** power / sum(nonclipped)) for power in range(1, polypower+1)]

lib.show_header("Calc. of baseline (%f reported)" % (lib.excind(calcs, 2000, 'baseline')))
lines = []
for year in range(2001, 2011):
    lines.append("weather_%d = [%s]" % (year, ','.join(["%.12g" % weday for weday in weather[year]])))
lines.append("bl1(weather) = sum([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, 2000, coeff) for coeff in coefflist]))
lines.append("bl2(weather) = (bl1([%s]) - 365 * bl1(%.12g .^ (1:%d)))" % ('; '.join(["weather'.^%d" % pow for pow in range(1, polypower+1)]), lib.excind(mintemps, 2009, 'analytic'), polypower))
if not skip_clipping:
    lines.append("bl(weather) = bl2(weather) .* (bl2(weather) .> 0)")
terms = []
for year in range(2001, 2011):
    terms.append("bl(weather_%d)" % (year))
lines.append("(" + ' + '.join(terms) + ") / 10")
lib.show_julia(lines)

if not skip_clipping:
    lib.show_header("Calc. of clipped days portion (%f reported)" % lib.excind(calcs, 2050, 'zero'))
    lines = ["weather_%d = [%s]" % (2050, ','.join(["%.12g" % weday for weday in weather[2050]])),
             "eff0(weather) = ([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, 2049, coeff) for coeff in coefflist]),
             "effadj(weather) = eff0([%s]) - eff0(%.12g .^ (1:%d))[1]" % ('; '.join(["weather'.^%d" % pow for pow in range(1, polypower+1)]), lib.excind(mintemps, 2009, 'analytic'), polypower),
             "mean(effadj(weather_%d) .<= 0)" % 2050]
    lib.show_julia(lines)

lib.show_header("Calc. of result (%f reported)" % (outputs[futureyear]['rebased']))

lib.show_header("  Without the goodmoney assumption:")
lines = ["weather_%d = [%s]" % (futureyear, ','.join(["%.12g" % weday for weday in weather[futureyear]])),
         "eff0(weather) = ([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, futureyear, coeff) for coeff in coefflist]),
         "effadj(weather) = eff0([%s]) - eff0(%.12g .^ (1:%d))[1]" % ('; '.join(["weather'.^%d" % pow for pow in range(1, polypower+1)]), lib.excind(mintemps, 2009, 'analytic'), polypower)]
if not skip_clipping:
    lines.append("efffin(weather) = sum(effadj(weather) .* (effadj(weather) .> 0))")
lines.append("efffin(weather_%d) - %.12g" % (futureyear, lib.excind(calcs, 2000, 'baseline')))
lib.show_julia(lines)

lib.show_header("  Using the no-anti-adaptation assumption")
lines = ["weather_%d = [%s]" % (futureyear, ','.join(["%.12g" % weday for weday in weather[futureyear]])),
         "eff0(weather) = ([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, futureyear, coeff) for coeff in coefflist]),
         "effadj(weather) = eff0([%s]) - eff0(%.12g .^ (1:%d))[1]" % ('; '.join(["weather'.^%d" % pow for pow in range(1, polypower+1)]), lib.excind(mintemps, 2009, 'analytic'), polypower),
         "efffin(weather) = effadj(weather) .* (effadj(weather) .> 0)",
         "original = efffin(weather_%d)" % futureyear,
         "gdpgammas = [%s]" % ', '.join(["%.12g" % csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['covarnames'][ii] == 'loggdppc']),
         "deltacoeff = gdpgammas .* (%.12g - %.12g)" % (lib.excind(preds, futureyear - 1, 'loggdppc'), lib.excind(preds, 2009, 'loggdppc')),
         "eff0(weather) = (([%s] - deltacoeff)' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, futureyear, coeff) for coeff in coefflist]),
         "effadj(weather) = eff0([%s]) - eff0(%.12g .^ (1:%d))[1]" % ('; '.join(["weather'.^%d" % pow for pow in range(1, polypower+1)]), lib.excind(mintemps, 2009, 'analytic'), polypower),
         "efffin(weather) = effadj(weather) .* (effadj(weather) .> 0)",
         "goodmoney = efffin(weather_%d)" % futureyear,
         "sum(min(original, goodmoney)) - %.12g" % lib.excind(calcs, 2000, 'baseline')]
lib.show_julia(lines)

lib.show_header("Climtas effect in %d (%f reported)" % (2050, outputs[2050]['climtas_effect']))
coeffs = [csvv['gamma'][ii] for ii in range(len(csvv['gamma'])) if csvv['covarnames'][ii] == 'climtas']
lines = ["weather_%d = [%s]" % (2050, ','.join(["%.12g" % weday for weday in weather[2050]])),
         "eff0(weather) = ([%s]' * weather) / 100000" % ', '.join(["%.12g" % lib.excind(calcs, 2050, coeff) for coeff in coefflist]), # NOTE: coeffs from 2050, ot 2049
         "effadj(weather) = eff0([%s]) - eff0(%.12g .^ (1:%d))[1]" % ('; '.join(["weather'.^%d" % pow for pow in range(1, polypower+1)]), lib.excind(mintemps, 2009, 'analytic'), polypower),
         "unclipped = effadj(weather_%d) .> 0" % 2050,
         "(" + ' + '.join(["%s * sum((weather_%d.^%d - %.12f^%d) .* unclipped')" % (coeffs[kk], 2050, kk+1, lib.excind(mintemps, 2009, 'analytic'), kk+1) for kk in range(polypower)]) + ")"]
lib.show_julia(lines, clipto=400)

