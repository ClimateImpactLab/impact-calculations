################################################
# GENERATE ADAPTATION COST CURVES 
# This is an attempt to generalize the code to be able to use any functional form estimated in the response function

# T. Carleton, 3/13/2017

# This version uses AVERAGE temperature exposure rather than ANNUAL

#### THIS VERSION INCORPORATES CLIPPING: We set adaptation costs to zero whenever the impact falls below zero.

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

#####################
is.local <- F
if(is.local) {
tavgpath = "~/Dropbox/Tamma-Shackleton/GCP/adaptation_costs/data/climtas.nc4"
tannpath = "~/Dropbox/Tamma-Shackleton/GCP/adaptation_costs/data/poly/"
outpath = "~/Tamma-Shackleton/GCP/adaptation_costs/data/poly"
impactspath <- "/Users/tammacarleton/Dropbox/Tamma-Shackleton/GCP/adaptation_costs/data/poly/global_interaction_Tmean-POLY-4-AgeSpec-geezer.nc4"
gammapath = "~/Dropbox/Tamma-Shackleton/GCP/adaptation_costs/data/poly/global_interaction_Tmean-POLY-4-AgeSpec.csvv"
gammarange = 13:24
minpath <- "~/Dropbox/Tamma-Shackleton/GCP/adaptation_costs/data/poly/global_interaction_Tmean-POLY-4-AgeSpec-geezer-polymins.csv"
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

# If polynomial, how many powers?
powers <- as.numeric(args[8])

# Details on the functional form
if(args[8]=='NS') {
  knots <- c(-12, -7, 0, 10, 18, 23, 28, 33)
}
if(args[8]=='LS'){
  knots <- c(-10, 0, 10, 20, 28, 33)
}
if(args[8]=='poly'){
  powers <- as.numeric(substr(args[7],5,5))
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

###############################################
#  Get spline reference temperatures from CSV
###############################################

splinemins <- read.csv(minpath, header=T)

##############################################################################################
# LOAD realized climate variable from single folder
##############################################################################################

# OPEN THE NETCDF - average temps
nc.tavg <- nc_open(tavgpath)
temps.avg <- ncvar_get(nc.tavg, 'averaged') #average temperatures
regions <- ncvar_get(nc.tavg, 'regions')
year.avg <- ncvar_get(nc.tavg, 'year')

## NOTE: Need to generalize this for Jiacan's other output (not sure how general her files are)
if (model=="spline") {
  
  tannpath <- paste0('/shares/gcp/climate/BCSD/aggregation/cmip5_new/IR_level/', rcp, '/cubic_spline_tas/', length(knots), 'knots/tas_restrict_cubic_spline_aggregate_', rcp, '_r1i1p1_', climmodel, '.nc')
  
  nc.tann <- nc_open(tannpath)
  year.ann <- ncvar_get(nc.tann, 'year')
  temps.ann.spline0 <- ncvar_get(nc.tann, 'tas_sum') #realized temperatures
  temps.ann.splineK <- ncvar_get(nc.tann, 'spline_variables')
  # Combine tas_sum with spline terms
  temps.ann <- array(NA, dim = c(dim(temps.ann.splineK)[1], length(knots)-1, length(year.ann)))
  temps.ann[,1,] <- temps.ann.spline0
  temps.ann[,2:(length(knots)-1),] <- temps.ann.splineK
  rm(temps.ann.spline0, temps.ann.splineK)
}

if (model=="poly") {
  
  # Get first power from James' test files
  temps.ann1 <- ncvar_get(nc.tavg, 'annual')*365
  
  # Fill in an R-by-#powers array with all annual clim data
  temps.ann <- array(NA, dim = c(dim(temps.ann1)[1], powers, length(year.avg[year.avg>=2006])))
  temps.ann[,1,] <- temps.ann1[,which(year.avg>=2006)]
  rm(temps.ann1)
  
  # Loop over polynomial power subfolders (change this if Jiacan changes her folder structure)
  for(p in 2:powers) {
    
    tannpath <- paste0('/shares/gcp/climate/BCSD/aggregation/cmip5/IR_level/', rcp, '/', climmodel, '/tas_power', p, '/tas_annual_aggregated_',rcp, '_r1i1p1_', climmodel, '.nc')
    
    nc.tann <- nc_open(tannpath)
    temporary <- ncvar_get(nc.tann, 'tas')*365
    temps.ann[,p,] <- temporary 
    rm(temporary)
  }
  year.ann <- ncvar_get(nc.tann, 'year')
}

if (model == "bin") {
  #temps.ann <- ncvar_get(nc.tann, 'bin_variables')
  print("NEED TO FORMAT FOR POLYNOMIALS -- SEE JIACAN's POLYNOMIAL FILES")
}

rm(nc.tann, nc.tavg)

print("ANNUAL AND LONG RUN AVERAGE TEMPERATURES LOADED")


##############################################################################################
# LOAD IMPACTS 
##############################################################################################

nc.imp <- nc_open(impactspath)
impacts.positive <- ncvar_get(nc.imp, 'positive') # Clipped value
impacts.rebased <- ncvar_get(nc.imp, 'rebased') # Clipped value
rm(nc.imp)

print("IMPACTS LOADED")

##############################################################################################
# Generate moving averages of each term in the spline, poly, or binned variables
##############################################################################################

# 15-year moving average of each term
movingavg <- array(NA, dim=dim(temps.ann))

R <- dim(temps.ann)[1]
S <- dim(temps.ann)[2] # K = no. clim vars * no. clim covars, but S = no. clim vars

for(r in 1:R) { #loop over all regions
  for(s in 1:S) { # loop over all spline terms or poly terms
    if (sum(is.finite(temps.ann[r,s,])) > 0)
      movingavg[r,s,] <- ave(temps.ann[r,s,], FUN=function(x) rollmean(x, k=15, fill="extend"))
  }
}
print("MOVING AVERAGE OF ANNUAL TEMPERATURES CALCULATED")

##############################################################################################
# For non-binned models, generate the value for each climate variable that we subtract off
##############################################################################################

if (model=="spline") {
  
  # Create an R x S array of spline reference terms for each impact region
  terms_ref <- array(NA, dim=c(dim(movingavg)[1], dim(movingavg)[2]))
  N <- length(knots) # How many knots

for (r in 1:R) { 
  rindex <- which(splinemins$region==regions[r]) # just in case they are not ordered the same way
  ref <- splinemins$analytic[rindex]
  terms_ref[r,1] <- ref
  for(n in 1:(N-2)) {
    terms_ref[r,1+n] <- (ref-knots[n])^3 * (ref>knots[n]) 
    - (ref-knots[N-1])^3 * (ref>knots[N-1]) * ((knots[N]-knots[n])/(knots[N]-knots[N-1]))
    + (ref-knots[N])^3 * (ref>knots[N]) * ((knots[N-1]-knots[n])/(knots[N]-knots[N-1]))
  }
}
  terms_ref <- terms_ref*365 # to make it annual sum of the spline terms
  print("SPLINE TERMS FOR THE REFERENCE TEMPERATURE CALCULATED")
}

if (model=="bin") {
  print("REFERENCE TEMPERATURE NOT NEEDED FOR BINNED MODEL")
}

if (model=="poly") {
  
  # Create an R x S array of poly reference terms for each impact region
  terms_ref <- array(NA, dim=c(dim(movingavg)[1], dim(movingavg)[2]))
  N <- powers # How many knots
  
  for (r in 1:R) { 
    rindex <- which(splinemins$region==regions[r]) # just in case they are not ordered the same way
    ref <- splinemins$analytic[rindex] # this is a scalar -- CHANGE THIS BACK!! JAMES NEEDS TO FIX THE ANALYTIC SOLUTION
    for(n in 1:N-1) {
      terms_ref[r,n] <- ref^n 
    }
  }
  terms_ref <- terms_ref*365 # to make it annual sum of the poly terms
  print("POLYNOMIAL TERMS FOR THE REFERENCE TEMPERATURE CALCULATED")
}


###############################################
# For each region-year, calculate lower and upper bounds
###############################################

# If the number of climate covariates is less than the number of climate variables, we need to expand
if(length(dim(temps.avg)) < length(dim(temps.ann))) {
  new <- array(NA, dim=c(dim(temps.avg)[1],K,tail(dim(temps.avg), n=1)))
  for (k in 1:K) {
    new[,k,] <- temps.avg
  }
  temps.avg <- new
  rm(new)
  print("I'm assuming this single climate covariate gets multiplied by all climate variables")
}
if(length(dim(temps.avg)) == length(dim(temps.ann)) & dim(temps.avg)[2] < dim(temps.ann)[2]) {
  print("NEED TO FORMAT THIS CASE")
  if(dim(temps.avg) == dim(temps.ann)) {
    print("Do nothing -- each climate variable has its own average climate covariate")
  }
}

# Subset to get the average climate values that cover the same years as annual climate values
yearstokeep <- which(year.avg %in% year.ann)
temps.avg <- temps.avg[,,yearstokeep[1]:tail(yearstokeep, n =1)]

# Initialize -- region by lb/ub by year 
results <- array(0, dim=c(dim(temps.ann)[1], 2, dim(temps.ann)[3]) )

# Loop: for each impact region and each year, calculate bounds
for (r in 1:R){
  for (k in 1:K) {
    
    options(warn=-1)
    # Need a lead variable of the moving avg temp
    tempdf <- as.data.frame(movingavg[r,k,])
    colnames(tempdf) <- "climvar"
    ann <- slide(tempdf, Var='climvar', NewVar = 'future', slideBy=1, reminder=F)
    rm(tempdf)
    
    # Need a differenced variable for each climate covariate
    tempdf <- as.data.frame(temps.avg[r,k,])
    colnames(tempdf) <- "climcov"
    avg <- slide(tempdf, Var="climcov", NewVar = 'future', slideBy=1, reminder=F)
    avg$diff <- avg$climcov - avg$future
    rm(tempdf)
    options(warn=0)
    
    # Lower and upper bounds
    results[r,1,] <- results[r,1,] + avg$diff * (ann$climvar - terms_ref[r,k]) * gammas[k] # lower
    results[r,2,] <- results[r,2,] + avg$diff * (ann$future - terms_ref[r,k]) * gammas[k] # upper
    
    # Clear 
    rm(avg, ann)
  }
  
  # Track progress
  if (r/10 == round(r/10)) {
    print(paste0("------- REGION ", r, " FINISHED ------------"))  
  }
  
}

###############################################
# CLIP, ADD ZEROs AT START, CUMULATIVELY SUM
###############################################

#Add in costs of zero for initial years
if (length(year.avg) > length(year.ann)) {
  add <- length(year.avg) - length(year.ann)
  resultsnew <- array(NA, dim = c(dim(results)[1], dim(results)[2], (dim(results)[3]+add)))
  
  # First set of years have zero costs, until changing temperatures kick in
  for (a in 1:add) {
    resultsnew[,,a] <- 0
  }
  resultsnew[,,(a+1):dim(resultsnew)[3]] <- results
  results <- resultsnew
  rm(resultsnew)
}

# CLIP all values where impacts are zero from James' clipped version of output
if (dim(results)[3]!=dim(impacts.positive)[2]) stop() 
for (r in 1:R) {
  for (y in 2:dim(results)[3]) {
    if (impacts.positive[r,y] == 0 & (impacts.rebased[r,y] - impacts.rebased[r,y-1] ==0)) {
      results[r,,y] <- 0 
    } 
  }
  if (impacts.positive[r,1] == 0 ) {
    results[r,,1] <- 0
  }
  
  # Cumulative sum over all years
  results[r,1,] <- cumsum(results[r,1,])
  results[r,2,] <- cumsum(results[r,2,])
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

vars <- list(varregion, varyear, varcosts_lb, varcosts_ub)

# Filepath for cost output
outpath <- gsub(".nc4", "-costs.nc4", impactspath)

cost_nc <- nc_create(outpath, vars)
print("CREATED NEW NETCDF FILE")

ncvar_put(cost_nc, varregion, regions)
ncvar_put(cost_nc, varyear, year)
ncvar_put(cost_nc, varcosts_lb, results[,1 ,])
ncvar_put(cost_nc, varcosts_ub, results[,2 ,])
nc_close(cost_nc)

print("----------- DONE DONE DONE ------------")

print("----------- DONE DONE DONE ------------")

print("----------- DONE DONE DONE ------------")

print("----------- DONE DONE DONE ------------")