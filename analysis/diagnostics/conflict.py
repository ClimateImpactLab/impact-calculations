import sys, os, csv
from netCDF4 import Dataset
import numpy as np
import lib, shortterm

dir = sys.argv[1]
csvvdir = "/shares/gcp/social/parameters/conflict/hierarchical_08102017"
do_adm0 = False
region = "IND.33.542.2153"
period0 = 687
periodN = 694

if do_adm0:
    onlymodel = "global_interactionadm0_withpopop_weighted_08102017_intergroup"
else:
    onlymodel = "global_interactionadm2_withpopop_weighted_08102017_interpersonal"

lib.show_header("The Covariates File (betas):")
beta_header, betas = shortterm.get_excerpt(os.path.join(dir, onlymodel + "-betas.csv"), region)

lib.show_header("The Coefficients File (final):")
final_header, finals = shortterm.get_excerpt(os.path.join(dir, onlymodel + "-final.csv"), region)

lib.show_header("The Sub-Calculations")
outputs = lib.get_outputs(os.path.join(dir, onlymodel + '.nc4'), [period0, periodN], region, timevar='month')

## Figure out which region this is
if do_adm0:
    regionindex = np.array(list(lib.get_adm0_regionindices(region[:3])))
else:
    regionindex = lib.get_regionindex(region)

lib.show_header("Predictor data:")
rootgrp = Dataset("/shares/gcp/climate/IRI/final_v2/tas_aggregated_forecast_Feb-Jun2017.nc", 'r', format='NETCDF4')
month0 = rootgrp.variables['S'][0] + rootgrp.variables['L'][0]
calmonth0 = int(month0 - 0.5) % 12
tas0 = np.mean(rootgrp.variables['mean'][0, 0, regionindex])
monthN = rootgrp.variables['S'][-1] + rootgrp.variables['L'][-1]
calmonthN = int(monthN - 0.5) % 12
tasN = np.mean(rootgrp.variables['mean'][-1, -1, regionindex])
rootgrp = Dataset("/shares/gcp/climate/IRI/final_v2/prcp_aggregated_forecast_Feb-Jun2017.nc", 'r', format='NETCDF4')
pr0 = np.mean(rootgrp.variables['mean'][0, 0, regionindex])
prN = np.mean(rootgrp.variables['mean'][-1, -1, regionindex])
rootgrp = Dataset("/shares/gcp/climate/IRI/final_v2/tas_aggregated_climatology_1982-2010.nc", 'r', format='NETCDF4')
tmean0 = np.mean(rootgrp.variables['tas'][calmonth0, regionindex])
tmeanN = np.mean(rootgrp.variables['tas'][calmonthN, regionindex])
if do_adm0:
    rootgrp = Dataset("/shares/gcp/climate/IRI/final_v2/tas_aggregated_historical_std_1982-2010_ISO.nc", 'r', format='NETCDF4')
    tstd0 = rootgrp.variables['tas'][calmonth0, list(rootgrp.variables['ISO']).index(region[:3])]
    tstdN = rootgrp.variables['tas'][calmonthN, list(rootgrp.variables['ISO']).index(region[:3])]
else:
    rootgrp = Dataset("/shares/gcp/climate/IRI/final_v2/tas_aggregated_historical_std_1982-2010_IR.nc", 'r', format='NETCDF4')
    tstd0 = np.mean(rootgrp.variables['tas'][calmonth0, regionindex])
    tstdN = np.mean(rootgrp.variables['tas'][calmonthN, regionindex])
rootgrp = Dataset("/shares/gcp/climate/IRI/final_v2/prcp_aggregated_climatology_1982-2010.nc", 'r', format='NETCDF4')
prmean0 = np.mean(rootgrp.variables['prcp'][calmonth0, regionindex])
prmeanN = np.mean(rootgrp.variables['prcp'][calmonthN, regionindex])

print ','.join(['month', 'calmonth', 'tas', 'tmean', 'tstd', 'pr', 'pr_mean'])
print ','.join(map(str, [month0, calmonth0, tas0, tmean0, tstd0, pr0, prmean0]))
print ','.join(map(str, [monthN, calmonthN, tasN, tmeanN, tstdN, prN, prmeanN]))

lib.show_header("CSVV:")
csvv = lib.get_csvv(os.path.join(csvvdir, onlymodel + ".csvv"))

lib.show_header("Interpolated z(tas) coefficient (%f reported)" % (betas[beta_header.index('beta-temp')]))
shortterm.show_coefficient(csvv, beta_header, betas, 'tas', {})

line1 = "pef(pr) = %f * (365.25 / 10) * pr + %f * ((365.25 / 10) * pr)^2" % (csvv['gamma'][csvv['prednames'].index('precip')], csvv['gamma'][csvv['prednames'].index('precip2')])

for period, tas, tmean, tstd, pr, prmean, result in [(period0, tas0, tmean0, tstd0, pr0, prmean0, finals[0]),
                                                     (periodN, tasN, tmeanN, tstdN, prN, prmeanN, finals[-1])]:
    lib.show_header("Temperature component in period %d (%f reported)" % (period, outputs[period]['response']))
    lib.show_julia("%f * (%f - %f) / %f" % (betas[beta_header.index('beta-temp')], tas, tmean, tstd))

    lib.show_header("Precipitation component in period %d (%f reported)" % (period, outputs[period]['response2']))
    lib.show_julia([line1, "pef(%f)" % pr])

    lib.show_header("Precipitation climate component in period %d (%f reported)" % (period, outputs[period]['climatic']))
    lib.show_julia([line1, "pef(%f)" % prmean])

    lib.show_header("Result in period %d (%f reported)" % (period, result))
    terms = ["%f * (%f - %f) / %f" % (betas[beta_header.index('beta-temp')], tas, tmean, tstd)]
    terms.append("pef(%f)" % pr)
    terms.append("-pef(%f)" % prmean)
    lines = [line1, " + ".join(terms)]
    lib.show_julia(lines)

