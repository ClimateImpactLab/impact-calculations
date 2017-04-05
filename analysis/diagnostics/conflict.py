import sys, os, csv
from netCDF4 import Dataset
import numpy as np
import lib, shortterm

dir = sys.argv[1]
csvvdir = "/shares/gcp/social/parameters/conflict/single_stage_03282017"
onlymodel = "OLS_interaction_m3_intergroup"

lib.show_header("The Covariates File (betas):")
beta_header, betas = shortterm.get_excerpt(os.path.join(dir, onlymodel + "-betas.csv"), 'IND.33.542.2153')

lib.show_header("The Coefficients File (final):")
final_header, finals = shortterm.get_excerpt(os.path.join(dir, onlymodel + "-final.csv"), 'IND.33.542.2153')

## Figure out which region this is
regionindex = lib.get_regionindex('IND.33.542.2153')

lib.show_header("Predictor data:")
rootgrp = Dataset("/shares/gcp/climate/IRI/tas_aggregated_forecast_2012-2017Mar.nc", 'r', format='NETCDF4')
month0 = rootgrp.variables['S'][0] + rootgrp.variables['L'][0]
calmonth0 = int(month0 - 1.5) % 12
tas0 = rootgrp.variables['mean'][0, 0, regionindex]
monthN = rootgrp.variables['S'][-1] + rootgrp.variables['L'][-1]
calmonthN = int(monthN - 5.5) % 12
tasN = rootgrp.variables['mean'][-1, -1, regionindex]
rootgrp = Dataset("/shares/gcp/climate/IRI/prcp_aggregated_forecast_2012-2017Mar.nc", 'r', format='NETCDF4')
sqrtp0 = rootgrp.variables['mean'][0, 0, regionindex]
sqrtpN = rootgrp.variables['mean'][-1, -1, regionindex]
rootgrp = Dataset("/shares/gcp/climate/IRI/tas_aggregated_climatology_1981-2010.nc", 'r', format='NETCDF4')
tmean0 = rootgrp.variables['mean'][calmonth0, 0, regionindex]
tstd0 = rootgrp.variables['stddev'][calmonth0, 0, regionindex]
tmeanN = rootgrp.variables['mean'][calmonthN, -1, regionindex]
tstdN = rootgrp.variables['stddev'][calmonthN, -1, regionindex]
rootgrp = Dataset("/shares/gcp/climate/IRI/prcp_aggregated_climatology_1981-2010.nc", 'r', format='NETCDF4')
sqrtpmean0 = rootgrp.variables['mean'][calmonth0, 0, regionindex]
sqrtpmeanN = rootgrp.variables['mean'][calmonthN, -1, regionindex]

print ','.join(['month', 'calmonth', 'tas', 'tmean', 'tstd', 'sqrtp', 'sqrtp_mean'])
print ','.join(map(str, [month0, calmonth0, tas0, tmean0, tstd0, sqrtp0, sqrtpmean0]))
print ','.join(map(str, [monthN, calmonthN, tasN, tmeanN, tstdN, sqrtpN, sqrtpmeanN]))

lib.show_header("CSVV:")
csvv = lib.get_csvv(os.path.join(csvvdir, onlymodel + ".csvv"))

lib.show_header("Interpolated z(tas) coefficient (%f reported)" % (betas[beta_header.index('beta-temp')]))
shortterm.show_coefficient(csvv, beta_header, betas, 'tas', {})

line1 = "pef(sqrtp) = %f * (365.25 / 30) * sqrtp^2 + %f * ((365.25 / 30) * sqrtp^2)^2" % (csvv['gamma'][csvv['prednames'].index('precip')], csvv['gamma'][csvv['prednames'].index('precip2')])

lib.show_header("Result in first period (%f reported)" % finals[0])
terms = ["%f * (%f - %f) / %f" % (betas[beta_header.index('beta-temp')], tas0, tmean0, tstd0)]
terms.append("pef(%f)" % sqrtp0)
terms.append("-pef(%f)" % sqrtpmean0)
lines = [line1, " + ".join(terms)]
lib.show_julia(lines)

lib.show_header("Result in last period (%f reported)" % finals[-1])
terms = ["%f * (%f - %f) / %f" % (betas[beta_header.index('beta-temp')], tasN, tmeanN, tstdN)]
terms.append("pef(%f)" % sqrtpN)
terms.append("-pef(%f)" % sqrtpmeanN)
lines = [line1, " + ".join(terms)]
lib.show_julia(lines)
