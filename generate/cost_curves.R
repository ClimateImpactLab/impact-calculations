################################################
# GENERATE ADAPTATION COST CURVES using GCP output for mortality
# T. Carleton, 4/15/2016
###############################################

rm(list=ls())
library(ncdf4)

###############################################
# FOR REFERENCE: the calculation we are performing is:
# tbar_0[beta(y_0, p_0, tbar_0) - beta(y_0, p_0, tbar_1)] < COST < tbar_1[beta(y_1, p_1, tbar_0) - beta(y_1, p_1, tbar_1)]
# We calculate this for every year-region-bin, sum across bins for each region, sum across years (and eventually we will sum across regions)
###############################################

args = commandArgs(trailingOnly = TRUE)

# OPEN THE NETCDF - temps
filename.betas <- args[1]
nc.betas <- nc_open(filename.betas)
betas <- ncvar_get(nc.betas, 'betas')
regions <- ncvar_get(nc.betas, 'regions')
rm(nc.betas)

  # OPEN THE NETCDF - temps
  filename.temp <- args[2]
  nc.temps <- nc_open(filename.temp)
  temps.ann <- ncvar_get(nc.temps, 'annual') #realized temperatures
  temps.avg <- ncvar_get(nc.temps, 'averaged') #average temperatures
  regions <- ncvar_get(nc.temps, 'regions')
  year <- ncvar_get(nc.temps, 'year')
  rm(nc.temps)

  # read in estimate for dBeta/dTbar
  gammas = read.csv('/shares/gcp/data/adaptation/surface-space-all.csv', header=FALSE, col.names=c('method', 'binlo', 'binhi', 'intercept_coef', 'bindays_coef', 'gdppc_coef', 'popop_coef', 'intercept_serr', 'bindays_serr', 'gdppc_serr', 'popop_serr'), skip = 18)


  # counterfactual betas require dbeta/tbar: We need:
  ###### #1: beta(y_0, p_0, tbar_1) = beta(y_0, p_0, tbar_0) + dbeta/dtbar(tbar_1-tbar_0)
  ###### #2: beta(y_1, p_1, tbar_0) = beta(y_1, p_1, tbar_1) - dbeta/dtbar(tbar_1-tbar_0)
  dbeta <- gammas[gammas$method=='seemur' ,]
  rm(gammas)

  costs <- array(NaN, dim=c(2, dim(regions), dim(year)-1)) # First dimenstion: LOWER BOUND IN 1, UPPER BOUND IN 2

  for (r in 1:length(regions)) {
    costs_lb <- matrix(NaN, nrow=length(year)-1,ncol=11)
    costs_ub <- matrix(NaN, nrow=length(year)-1,ncol=11)
    for (i in 1:11) {
      clip <- (betas[r, -1 ,i] == betas[r, -119, i])
      costs_lb[,i] <- temps.ann[i,r,-119] * (-dbeta$bindays_coef[i]*(temps.avg[i,r,-1] - temps.avg[i,r,-119])) * !clip
      costs_ub[,i] <- temps.ann[i,r,-1] * (-dbeta$bindays_coef[i]*(temps.avg[i,r,-1] - temps.avg[i,r,-119])) * !clip
    }
    costs[1,r,] <- cumsum(rowSums(costs_lb, na.rm = TRUE))
    costs[2,r,] <- cumsum(rowSums(costs_ub, na.rm = TRUE))
    rm(list = c('costs_lb', 'costs_ub'))
  }

  rm(list = c('temps.ann', 'temps.avg'))

  yearminus <- year[-1]
  dimregions <- ncdim_def("region", units="" ,1:length(regions))
  dimtime <- ncdim_def("year",  units="", yearminus)

  varregion <- ncvar_def(name = "regions",  units="", dim=list(dimregions))
  varyear <- ncvar_def(name = "years",   units="", dim=list(dimtime))

  varcosts_lb <- ncvar_def(name = "costs_lb", units="deaths/100000", dim=list(dimregions, dimtime))
  varcosts_ub <- ncvar_def(name = "costs_ub", units="deaths/100000", dim=list(dimregions, dimtime))

  vars <- list(varregion, varyear, varcosts_lb, varcosts_ub)

  cost_nc <- nc_create(gsub('.nc4', '-costs.nc4', filename.betas), vars)
  ncvar_put(cost_nc, varregion, regions)
  ncvar_put(cost_nc, varyear, yearminus)
  ncvar_put(cost_nc, varcosts_lb, costs[1, ,])
  ncvar_put(cost_nc, varcosts_ub, costs[2, ,])
  nc_close(cost_nc)

