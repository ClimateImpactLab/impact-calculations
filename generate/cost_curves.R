
################################################
# GENERATE ADAPTATION COST CURVES
# This is an attempt to generalize the code to be able to use any functional form estimated in the response function

# T. Carleton, 3/13/2017

# UPDATE 04/25/2018: This version checks whether timesteps in the climate file are equivalent to timesteps in the impacts file  
# Assumption: the impacts file always has 120 time steps (i.e. goes to year 2100) while the climate file may have < 120 time steps (e.g. up to year 2099 or 2098)
# If found unequal, this code removes the last n columns in the impacts file corresponding to the difference in years

# UPDATE 06/19/2017: This version brings in daily clipped values of marginal temperature effects from James 
# This version uses AVERAGE temperature exposure rather than ANNUAL
# This includes TWO VERSIONS OF COSTS: one that cumulates year-to-year costs, and one that estimates costs independently in each year

#### Clipping: iWe set adaptation costs to zero whenever the impact falls below zero.

# FOR REFERENCE: the calculation we are performing is:
# tbar_0[beta(y_0, p_0, tbar_0) - beta(y_0, p_0, tbar_1)] < COST < tbar_1[beta(y_1, p_1, tbar_0) - beta(y_1, p_1, tbar_1)]
# We calculate this for every year-region-bin, sum across bins for each region, sum across years (and eventually we will sum across regions)

# This simplifies to: sum_k [ T_0^k * gamma_k * (Tbar_0^k - Tbar_1^k)] < COST < sum_k [ T_1^k * gamma_k * (Tbar_0^k - Tbar_1^k)], where "k" indicates each term in the nonlinear response (e.g. if it's a fourth order polynomial, we have k = 1,...,4), and where the Tbar values may vary by climate term (e.g for bins we interact each bin variable by the average number of days in that bin)

###########################
# Syntax: cost_curves(tavgpath, rcp, climate_model, impactspath), Where:
# tavgpath = filepath for long run average climate data by impact region year
# rcp = which RCP? enter as a string --  'rcp85' or 'rcp45'
# climate_model = which climate model? enter as a string -- e.g. 'MIROC-ESM'
# impactspath = filepath for the projected impacts for this model
###########################

###############################################

rm(list=ls())

library(pracma)
library(ncdf4)
library(dplyr)
library(DataCombine)
library(zoo)
library(abind)
library(rPython)
source("generate/stochpower.R")

#####################
is.local <- F
if(is.local) {
tavgpath = "~/Dropbox/Tamma-Shackleton/GCP/adaptation_costs/data/climtas.nc4"
tannpath = "~/Dropbox/Tamma-Shackleton/GCP/adaptation_costs/data/poly/"
outpath = "~/Tamma-Shackleton/GCP/adaptation_costs/data/poly_dailyclip"
impactspath <- "/Users/tammacarleton/Dropbox/Tamma-Shackleton/GCP/adaptation_costs/data/poly_dailyclip/global_interaction_Tmean-POLY-4-AgeSpec-oldest.nc4"
gammapath = "~/Dropbox/Tamma-Shackleton/GCP/adaptation_costs/data/poly_dailyclip/global_interaction_Tmean-POLY-4-AgeSpec.csvv"
gammarange = 25:36 #oldest! 
minpath <- "~/Dropbox/Tamma-Shackleton/GCP/adaptation_costs/data/poly_dailyclip/global_interaction_Tmean-POLY-4-AgeSpec-oldest-polymins.csv"
model <- 'poly'
powers <- 4
avgmethod = 'bartlett'
}
#####################

###############################################
# Set up
###############################################

args <- commandArgs(trailingOnly=T)

# Filepath for climate covariates and annual temperatures by region-year through 2100
tavgpath = args[1] # outputs/temps/RCP/GCM/climtas.nc4
rcp = args[2]
climmodel = args[3]

# Filepath for impacts
impactspath <- args[4] # paste0("outputs/", sector, "/", impactsfolder, "/median-clipped/rcp", rcp, "/", climmodel, "/high/SSP4/moratlity_cubic_splines_2factors_", climdata, "_031617.nc4")

# Averaging method
#avgmethod = args[5]
avgmethod = 'bartlett'

##############################################################################################
# LOAD realized climate variable from single folder
##############################################################################################

# OPEN THE NETCDF - average temps
nc.tavg <- nc_open(tavgpath)
temps.avg <- ncvar_get(nc.tavg, 'averaged') #average temperatures
regions <- ncvar_get(nc.tavg, 'regions')
year.avg <- ncvar_get(nc.tavg, 'year')

##############################################################################################
# LOAD ADAPTIVE INVESTMENTS TERM -- FROM JAMES' OUTPUT
##############################################################################################

nc.imp <- nc_open(impactspath)
impacts.climtaseff <- ncvar_get(nc.imp, 'climtas_effect') # Sum of adaptive investments at daily level

#check whether timesteps in climate file = timesteps in impacts file
if (length(year.avg) != length(ncvar_get(nc.imp, 'year'))) { 
  diff <- length(ncvar_get(nc.imp, 'year')) - length(year.avg) # calculate difference where impacts file is always assumed to have 120 time steps (i.e. up to year 2100) while climate file may have < 120 time steps (e.g. up to year 2099 or 2098)
  impacts.climtaseff <- data.frame(ncvar_get(nc.imp, 'climtas_effect')) #convert matrix to dataframe
  impacts.climtaseff <- impacts.climtaseff[,1:(ncol(impacts.climtaseff)-diff)] # remove last n columns which correspond to difference 
  impacts.climtaseff <- as.matrix(impacts.climtaseff) # convert dataframe back to matrix
}

rm(nc.imp)

if (length(dim(impacts.climtaseff)) == 1) {
    extended <- matrix(0, 1, length(impacts.climtaseff))
    extended[1,] <- impacts.climtaseff
    impacts.climtaseff <- extended
    temps.avg <- temps.avg[regions == 'IND.33.542.2153',, drop=F]
    regions <- c('IND.33.542.2153')
}

print("IMPACTS LOADED")

##############################################################################################
# Generate a moving average of the adaptive investments term
##############################################################################################

# 15-year moving average 
movingavg <- array(NA, dim=dim(impacts.climtaseff))

R <- dim(impacts.climtaseff)[1]

if(avgmethod == 'bartlett') {
# BARTLETT KERNEL
for(r in 1:R) { #loop over all regions
    if (sum(is.finite(impacts.climtaseff[r,])) > 0)
      tempdf <- impacts.climtaseff[r,]
      movingavg[r,] <- movavg(tempdf,30,'w')
  }
}

if(avgmethod=='movingavg') {
  for(r in 1:R) { #loop over all regions
    if (sum(is.finite(impacts.climtaseff[r,])) > 0)
    movingavg[r,] <- ave(impacts.climtaseff[r,], FUN=function(x) rollmean(x, k=15, fill="extend"))
  }
}

print("MOVING AVERAGE OF ADAPTIVE INVESTMENTS CALCULATED")

###############################################
# For each region-year, calculate lower and upper bounds
###############################################

# Initialize -- region by lb/ub by year
results <- array(0, dim=c(dim(temps.avg)[1], 2, dim(temps.avg)[2]) )
results_cum <- array(0, dim=c(dim(temps.avg)[1], 2, dim(temps.avg)[2]) )

# Loop: for each impact region and each year, calculate bounds
for (r in 1:R){

    options(warn=-1)
    # Need a lag variable of the expected value of adaptive investments term
    tempdf <- as.data.frame(movingavg[r,])
    colnames(tempdf) <- "climvar"
    expect <- slide(tempdf, Var='climvar', NewVar = 'lag', slideBy=-1, reminder=F)
    rm(tempdf)
    
    # COSTS: "EXACT" VERSION 
    avg <- as.data.frame(temps.avg[r,])
    colnames(avg) <- "climcov"
    avg$diff <- avg$climcov[which(year.avg==2010)] - avg$climcov 
    
    # COSTS: CUMULATIVE COSTS VERSION
    tempdf <- as.data.frame(temps.avg[r,])
    colnames(tempdf) <- "climcov"
    avg2 <- slide(tempdf, Var="climcov", NewVar = 'lag', slideBy=-1, reminder=F)
    avg2$diff <- avg2$lag - avg2$climcov
    rm(tempdf)
    options(warn=0)

    # Lower and upper bounds
    results[r,1,] <-  avg$diff * (expect$climvar[which(year.avg==2010)])  # lower
    results[r,2,] <-  avg$diff * (expect$climvar) # upper
    results_cum[r,1,] <-  avg2$diff * (expect$lag) # lower
    results_cum[r,2,] <-  avg2$diff * (expect$climvar) # upper
    
    # Clear
    rm(avg, expect)
 
  # Track progress
  if (r/1000 == round(r/1000)) {
    print(paste0("------- REGION ", r, " FINISHED ------------"))
  }
}

###############################################
# CLIP, ADD ZEROs AT START, CUMULATIVELY SUM
###############################################

#Add in costs of zero for initial years
  baseline <- which(year.avg==2015)
  for (a in 1:baseline) {
    results[,,a] <- matrix(0,dim(results)[1], dim(results)[2])
    results_cum[,,a] <- matrix(0,dim(results_cum)[1], dim(results_cum)[2])
  }

# Cumulative sum over all years for cumulative results
for (r in 1:R) {
  results_cum[r,1,] <- cumsum(results_cum[r,1,])
  results_cum[r,2,] <- cumsum(results_cum[r,2,])
}

###############################################
# Export as net CDF
###############################################

year <- year.avg
dimregions <- ncdim_def("region", units="" ,1:R)
dimtime <- ncdim_def("year",  units="", year)

varregion <- ncvar_def(name = "regions",  units="", dim=list(dimregions))
varyear <- ncvar_def(name = "years",   units="", dim=list(dimtime))

varcosts_lb <- ncvar_def(name = "costs_lb", units="deaths/100000", dim=list(dimregions, dimtime))
varcosts_ub <- ncvar_def(name = "costs_ub", units="deaths/100000", dim=list(dimregions, dimtime))
varcosts_lb_cum <- ncvar_def(name = "costs_lb_cum", units="deaths/100000", dim=list(dimregions, dimtime))
varcosts_ub_cum <- ncvar_def(name = "costs_ub_cum", units="deaths/100000", dim=list(dimregions, dimtime))

vars <- list(varregion, varyear, varcosts_lb, varcosts_ub, varcosts_lb_cum, varcosts_ub_cum)

# Filepath for cost output
outpath <- gsub(".nc4", "-costs.nc4", impactspath)

cost_nc <- nc_create(outpath, vars)

print("CREATED NEW NETCDF FILE")

ncvar_put(cost_nc, varregion, regions)
ncvar_put(cost_nc, varyear, year)
ncvar_put(cost_nc, varcosts_lb, results[,1 ,])
ncvar_put(cost_nc, varcosts_ub, results[,2 ,])
ncvar_put(cost_nc, varcosts_lb_cum, results_cum[,1 ,])
ncvar_put(cost_nc, varcosts_ub_cum, results_cum[,2 ,])
nc_close(cost_nc)

print("----------- DONE DONE DONE ------------")
