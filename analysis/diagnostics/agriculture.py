import os, sys
import numpy as np
import lib

dir = sys.argv[1]

weathertemplate_tas = "/shares/gcp/climate/BCSD/hierid/popwt/daily/tas/{0}/CCSM4/{1}/1.5.nc4"
weathertemplate_edd = "/shares/gcp/climate/BCSD/Agriculture/Degree_days/snyder/{0}/CCSM4/Degreedays_aggregated_{0}_CCSM4_cropwt_{1}.nc"
weathertemplate_prm = "/shares/gcp/climate/BCSD/aggregation/cmip5/IR_level/{0}/CCSM4/pr/pr_day_aggregated_{0}_r1i1p1_CCSM4_{1}.nc"
csvvmodel = "soy_global_tbarbr_lnincbr_ir-171208"
model = "soy_global_tbarbr_lnincbr_ir-171208"
futureyear = 2050
region = 'USA.14.608' #'IND.33.542.2153'
onlyreg = False

bin_edges = [-5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
             13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
             31, 32, 33, 34, 35, 36, 37, 38, 39, 40]

lib.show_header("The Predictors File (allcalcs):")
calcs = lib.get_excerpt(os.path.join(dir, "allmodels-allcalcs-%s.csv" % model), 2, region, range(2000, 2011) + [futureyear-1, futureyear], hasmodel=False)

lib.show_header("Season range:")
seasons = lib.get_region_data("/shares/gcp/social/baselines/agriculture/world-combo-201710-growing-seasons-soy.csv", region)

def sslice(suffix):
    return slice(int(seasons['plant_' + suffix]) - 1, int(seasons['harvest_' + suffix]) - 1)

lib.show_header("Weather (tas):")
wtas = lib.get_weather(weathertemplate_tas, [1981] + range(2001, 2011) + [futureyear-1, futureyear], region, variable='tas', subset=sslice('date'))

shapenum = lib.get_regionindex(region)

lib.show_header("Weather (edd):")
wedd = lib.get_weather(weathertemplate_edd, [1981] + range(2001, 2011) + [futureyear-1, futureyear], shapenum, variable='EDD_agg', regindex='SHAPENUM', subset=([bin_edges.index(8), bin_edges.index(30)], sslice('month')))

lib.show_header("Weather (prm):")
wprm = lib.get_weather(weathertemplate_prm, [1981] + range(2001, 2011) + [futureyear-1, futureyear], shapenum, variable='pr', regindex='SHAPENUM', subset=sslice('date'))

lib.show_header("CSVV:")
csvv = lib.get_csvv("/shares/gcp/social/parameters/agriculture/soy/%s.csvv" % csvvmodel)

lib.show_header("Outputs:")
outputs = lib.get_outputs(os.path.join(dir, model + '.nc4'), [1981, futureyear-1, futureyear], region)

for year in [2000, futureyear]:
    lib.show_header("Calc of gdd coeff in %s (%.12g reported):" % (year, lib.excind(calcs, year, 'coeff-gdd-8-30')))
    lib.show_coefficient(csvv, calcs, year, 'gdd-8-30', {})

lib.show_header("Un-rebased value in 1981 (%.12g reported):" % outputs[1981]['sum'])
line_wgdd = "wgdd_%d = [%s] - [%s]" % (1981, ','.join(["%.12g" % weday for weday in wedd[1981][0, :]]), ','.join(["%.12g" % weday for weday in wedd[1981][1, :]]))
line_wkdd = "wkdd_%d = [%s]" % (1981, ','.join(["%.12g" % weday for weday in wedd[1981][1, :]]))
line_wprm = "wprm_%d = [%s]" % (1981, ','.join(["%.12g" % weday for weday in wprm[1981]]))

lines = []    
lines.append("f_gk(gdd, kdd) = %.12g * sum(gdd) + %.12g * sum(kdd)" % (lib.excind(calcs, 2000, 'coeff-gdd-8-30'), lib.excind(calcs, 2000, 'coeff-kdd-30')))
lines.append("f_pr(pr) = %.12g * sum(pr) + %.12g * sum(pr.^2)" % (lib.excind(calcs, 2000, 'coeff-prmm'), lib.excind(calcs, 2000, 'coeff-prmm2')))
lines.append("f_gk(wgdd_1981, wkdd_1981) + f_pr(wprm_1981)")

lib.show_julia([line_wgdd, line_wkdd, line_wprm] + lines, clipto=200)

lib.show_header("Un-rebased value in 2050 (%.12g reported):" % outputs[2050]['sum'])
line_wgdd = "wgdd_%d = [%s] - [%s]" % (2050, ','.join(["%.12g" % weday for weday in wedd[2050][0, :]]), ','.join(["%.12g" % weday for weday in wedd[2050][1, :]]))
line_wkdd = "wkdd_%d = [%s]" % (2050, ','.join(["%.12g" % weday for weday in wedd[2050][1, :]]))
line_wprm = "wprm_%d = [%s]" % (2050, ','.join(["%.12g" % weday for weday in wprm[2050]]))

lines = []    
lines.append("f_gk(gdd, kdd) = %.12g * sum(gdd) + %.12g * sum(kdd)" % (lib.excind(calcs, futureyear, 'coeff-gdd-8-30'), lib.excind(calcs, futureyear, 'coeff-kdd-30')))
lines.append("f_pr(pr) = %.12g * sum(pr) + %.12g * sum(pr.^2)" % (lib.excind(calcs, futureyear, 'coeff-prmm'), lib.excind(calcs, futureyear, 'coeff-prmm2')))
lines.append("f_gk(wgdd_2050, wkdd_2050) + f_pr(wprm_2050)")

lib.show_julia([line_wgdd, line_wkdd, line_wprm] + lines, clipto=200)
