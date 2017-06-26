
################################################
# GENERATE ADAPTATION COST CURVES
# This is an attempt to generalize the code to be able to use any functional form estimated in the response function

# T. Carleton, 3/13/2017

# UPDATE 06/19/2017: This version brings in daily clipped values of marginal temperature effects from James 
# This version uses AVERAGE temperature exposure rather than ANNUAL
# This includes TWO VERSIONS OF COSTS: one that cumulates year-to-year costs, and one that estimates costs independently in each year

#### Clipping: iWe set adaptation costs to zero whenever the impact falls below zero.

# FOR REFERENCE: the calculation we are performing is:
# tbar_0[beta(y_0, p_0, tbar_0) - beta(y_0, p_0, tbar_1)] < COST < tbar_1[beta(y_1, p_1, tbar_0) - beta(y_1, p_1, tbar_1)]
# We calculate this for every year-region-bin, sum across bins for each region, sum across years (and eventually we will sum across regions)

# This simplifies to: sum_k [ T_0^k * gamma_k * (Tbar_0^k - Tbar_1^k)] < COST < sum_k [ T_1^k * gamma_k * (Tbar_0^k - Tbar_1^k)], where "k" indicates each term in the nonlinear response (e.g. if it's a fourth order polynomial, we have k = 1,...,4), and where the Tbar values may vary by climate term (e.g for bins we interact each bin variable by the average number of days in that bin)

###########################
# Syntax: cost_curves(tavgpath, rcp, climate_model, impactspath, gammapath, minpath, functionalform, 'ffparameters', 'gammarange'), Where:
# tavgpath = filepath for long run average climate data by impact region year
# rcp = which RCP? enter as a string --  'rcp85' or 'rcp45'
# climate_model = which climate model? enter as a string -- e.g. 'MIROC-ESM'
# impactspath = filepath for the projected impacts for this model
# gammapath = filepath for the CSVV of gammas
# minpath = filepath for the CSV of impact region-specific reference temperatures
# functionalform = 'spline', 'poly', or 'bin'
# 'ffparameters' = details on the functional form chosen. E.g. for spline, this can be 'LS' or 'NS', and for polynomial this can be 'poly4' or 'poly5'.
# gammarange = range of numbers indicating which of the gammas you want to pull (e.g. only a subset of them if you want just one age category) -- entered as a string!
###########################

###############################################

rm(list=ls())

library(ncdf4)
library(dplyr)
library(DataCombine)
library(zoo)
library(abind)
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

# Filepath for gammas -- where is the CSVV?
gammapath = args[5] # paste0("social/parameters/", sector, "/", csvname, ".csvv")

# Filepath for spline minimum values -- where is the CSV?
minpath = args[6] # paste0("social/parameters/mortality/mortality_splines_03162017/splinemins.csv")

# What model spec are you running? Options: bin, cubic spline, poly
model <- args[7]

# Details on the functional form
if(args[8]=='NS') {
  knots <- c(-12, -7, 0, 10, 18, 23, 28, 33)
}
if(args[8]=='LS'){
  knots <- c(-10, 0, 10, 20, 28, 33)
}
if(args[7]=='poly'){
  powers <- as.numeric(substr(args[8],5,5))
}

# Which gammas do you want to pull?
gammarange <- unlist(strsplit(args[9], ':'))
gammarange <- as.numeric(gammarange[1]):as.numeric(gammarange[2])

###############################################
#  Get Gammas from CSVVs
###############################################

csvv <- read.csv(gammapath, header=FALSE, skip = 18, strip.white=TRUE)

# Covariate names as listed in the csvv
row <- which(csvv[,1] == "covarnames")
covnames <- csvv[row+1,]

# Subset the covnames to only take the values for the subset called by the function (e.g. old age only)
covnames <- covnames[gammarange]

# Which covariates are climate covariates? (indicate climate covariates with a 1)
climdummy <- rep(NA, times=length(covnames))

for (i in 1:length(covnames)) {
  climdummy[i] <- (covnames[i]!='1' & covnames[i]!='logpopop' & covnames[i]!='loggdppc'  & covnames[i]!='lggdppc')
}

# IMPORTANT: the climate covariates need to be in the same order as the climate variables they get multiplied by
if (length(climdummy)!=length(covnames)) stop()

row <- which(csvv[,1] == "gamma")
gammas <- csvv[row+1,gammarange[1]:tail(gammarange,n=1)]
gammas <- gammas[which(climdummy == T)] # just the climate gammas extracted
gammas <- sapply(gammas, function(x) as.numeric(as.character(x)))

# How many climate variables interacted with climate covariates in the response function do we have?
K = length(covnames[covnames=="1"])

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
rm(nc.imp)

# NOTE: James' average climate effect terms need to be multiplied by 365 (as of June 24 2017 -- may update later when integrating updated climate data from Justin and Mike)
impacts.climtaseff <- impacts.climtaseff * 365

print("IMPACTS LOADED")

##############################################################################################
# Generate a moving average of the adaptive investments term
##############################################################################################

# 15-year moving average 
movingavg <- array(NA, dim=dim(impacts.climtaseff))

R <- dim(impacts.climtaseff)[1]

for(r in 1:R) { #loop over all regions
    if (sum(is.finite(impacts.climtaseff[r,])) > 0)
      movingavg[r,] <- ave(impacts.climtaseff[r,], FUN=function(x) rollmean(x, k=15, fill="extend"))
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
