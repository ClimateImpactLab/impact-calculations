
################################################
# GENERATE ADAPTATION COST CURVES
# MODIFIED FOR AG

# T. Carleton, 3/13/2017
# A. Hultgren 5/2/2019

# UPDATE 04/25/2018: This version checks whether timesteps in the climate file are equivalent to timesteps in the impacts file
# Assumption: the impacts file always has 120 time steps (i.e. goes to year 2100) while the climate file may have < 120 time steps (e.g. up to year 2099 or 2098)
# If found unequal, this code removes the last n columns in the impacts file corresponding to the difference in years

#### Clipping: Clipped portions of the response function do not contribute to adaptation costs.

#### Crop-specific configurations are set in ag_costs_config.R and read-in here.

#### Note: there are still some commented out lines or <if (1==0) { do test }> statements. These are for testing and can eventually be cleaned up.

###########################
# Syntax (bash): 
# Rscript tmp_and_prcp_costs.R "$base/batch$b" $crop $m $r $s $i 15 $seed 
# $base: the file path to the projection output directory tree. E.g.: '/shares/gcp/outputs/agriculture/impacts-mealy/montecarlo-sorghum-140521/montecarlo/'
# $b:    the batch number (integers 0-14)
# $crop: the crop as a string (e.g. 'maize')
# $m:    climate model (gcm name as a string)
# $r:    rcp (integers 45 or 85)
# $s:    ssp (integers 1-5)
# $i:    "iam" ('high' or 'low')
# 15:    the averaging period for the income covariate Bartlett kernel. This should not change.
# $seed: the seed value used to draw from the statistical uncertainty (as a string). If not running a Monte Carlo, set to ''.
###########################


###############################################

rm(list=ls())

require(dplyr)
library(pracma)
library(ncdf4)
library(abind)
library(matrixStats)
library(reticulate) # allow python to be called from R

#####################
is.local <- FALSE
exclude.rice.tmin.costs <- FALSE
output.csv <- FALSE

if(is.local) {
  # Andy's paths; need to change paths for a crop other than maize.

  configpath <- 'C:/Users/Andy Hultgren/Documents/ARE/GSR/GCP/bitbucket/ClimateImpactLab/impact-calculations/impacts/agriculture/ag_costs_config.R'

  use_python('C:/Users/Andy Hultgren/AppData/Local/Programs/Python/Python36/python.exe') # tell reticulate where to look for py36

  setwd('C:/Users/Andy Hultgren/Documents/ARE/GSR/GCP/Ag/Projections/adaptation_costs_test/impacts-mealy/single-corn-pbarspline-200423-partialder-fix')

  # Paths -- set for maize; update for a different crop
  incpath <- '../other_covariates/SSP3_IAM-high_15yr-avg.nc4'
  irrpath <- '../other_covariates/irrigation_share.nc4'
  tavgpath <- '../climate_data/maize_seasonaltasmax.nc4'# 'single-corn-kdd-cutoff31-precip-bins-costs/corn-allcalcs-191220.csv'
  pavgpath <- '../climate_data/maize_seasonalpr.nc4'
  ddpath <- '../climate_data/maize_seasonaledd.nc4'
  prpath <- '../climate_data/maize_monthbinpr.nc4'
  tminpath <- '../climate_data/rice_seasonaltmin.nc4'
  gammapath <- 'csvv/corn-200316.csvv'
  marginalspath <- 'corn-200423.nc4'
  outpath <- 'output'

  # allcalcs file needed for income and irrigation covariates, to determine the clipping filter (assign zero costs to clipped parts of the response)
  allcalcspath <- 'corn-allcalcs-200423.csv'

  crop <- 'maize'

  # Set to NA unless replicating a Monte Carlo draw, in which case pass the seed value used for the draw
  seed <- 12345

} else {


  if (1==0) {
    # For testing
    crop <- 'maize'
    model <- 'CCSM4'
    rcp <- '85'
    ssp <- '3'
    iam <- 'high'
    avg.period <- 15
    wd <- '/shares/gcp/outputs/agriculture/impacts-mealy/median-corn-pbarspline-200427/'
  }

  args <- commandArgs(trailingOnly=T)

  wd <- args[1]
  crop <- args[2]
  model <- args[3]
  rcp <- args[4]
  ssp <- args[5]
  iam <- args[6]
  avg.period <- args[7]
  seed <- args[8] # seed value for a Monte Carlo draw (if not calculating MC costs, set <seed> to '')

  # Filepath for impacts
  impactspath <- args[4] # paste0("outputs/", sector, "/", impactsfolder, "/median-clipped/rcp", rcp, "/", climmodel, "/high/SSP4/moratlity_cubic_splines_2factors_", climdata, "_031617.nc4")

  configpath <- paste0( pwd(), '/ag_costs_config.R' )

  setwd(wd)

  incpath <- paste0('/mnt/sacagawea_shares/gcp/social/baselines/agriculture/income_netcdfs/SSP', ssp, '_IAM-', iam, '_', avg.period, 'yr-avg.nc4')
  irrpath <- paste0('/mnt/sacagawea_shares/gcp/social/baselines/agriculture/income_netcdfs/irrigation_share.nc4')
  tavgpath <- paste0('/mnt/sacagawea_shares/gcp/outputs/temps/rcp', rcp,'/', model,'/', crop, '_seasonaltasmax.nc4')
  pavgpath <- paste0('/mnt/sacagawea_shares/gcp/outputs/temps/rcp', rcp,'/', model,'/', crop, '_seasonalpr.nc4')
  ddpath <- paste0('/mnt/sacagawea_shares/gcp/outputs/temps/rcp', rcp,'/', model,'/', crop, '_seasonaledd.nc4')
  prpath <- paste0('/mnt/sacagawea_shares/gcp/outputs/temps/rcp', rcp,'/', model,'/', crop, '_monthbinpr.nc4')
  outpath <- paste0('rcp', rcp, '/', model, '/', iam, '/SSP', ssp)
  print(paste0('outpath is: ', outpath, '/adaptation_costs.nc4'))

  if ((crop == 'rice') | (crop == 'wheat-spring')) {
    tminpath <- paste0('/mnt/sacagawea_shares/gcp/outputs/temps/rcp', rcp,'/', model,'/', crop, '_seasonaltasmin.nc4')
  }

  if (crop == 'wheat-winter') {
    # Winter wheat has all its own weather paths, due to the fall/winter/summer seasons.
    
    # Tavg and Pavg are the same for all seasons by definition, so just load the summer copy of the file.
    tavgpath <- paste0('/mnt/sacagawea_shares/gcp/outputs/temps/rcp', rcp,'/', model,'/', crop, '-summer_seasonaltasmax.nc4')
    pavgpath <- paste0('/mnt/sacagawea_shares/gcp/outputs/temps/rcp', rcp,'/', model,'/', crop, '-summer_seasonalpr.nc4')
    
    # For winter wheat, the season without a season name appended (to mirror other crops) is spring/summer.
    ddpath.fall <- paste0('/mnt/sacagawea_shares/gcp/outputs/temps/rcp', rcp,'/', model,'/', crop, '-fall_seasonaledd.nc4')
    ddpath.wint <- paste0('/mnt/sacagawea_shares/gcp/outputs/temps/rcp', rcp,'/', model,'/', crop, '-winter_seasonaledd.nc4')
    ddpath <- paste0('/mnt/sacagawea_shares/gcp/outputs/temps/rcp', rcp,'/', model,'/', crop, '-summer_seasonaledd.nc4')
    
    prpath.fall <- paste0('/mnt/sacagawea_shares/gcp/outputs/temps/rcp', rcp,'/', model,'/', crop, '-fall_monthbinpr.nc4')
    prpath.wint <- paste0('/mnt/sacagawea_shares/gcp/outputs/temps/rcp', rcp,'/', model,'/', crop, '-winter_monthbinpr.nc4')
    prpath <- paste0('/mnt/sacagawea_shares/gcp/outputs/temps/rcp', rcp,'/', model,'/', crop, '-summer_monthbinpr.nc4')
    
    tminpath.wint <- paste0('/mnt/sacagawea_shares/gcp/outputs/temps/rcp', rcp,'/', model,'/', crop, '-winter_seasonaltasmin.nc4')
    tminpath <- paste0('/mnt/sacagawea_shares/gcp/outputs/temps/rcp', rcp,'/', model,'/', crop, '-summer_seasonaltasmin.nc4')
  }
}

# Load crop-specific configurations for costs
source(configpath)




#####################


print('------------------')
print(paste0('Calculating costs for ', crop, ' under model ', model, ' / RCP ', rcp, ' / SSP', ssp, ' / IAM-',iam))
print('------------------')


##############################################################################################
# LOAD realized climate variable from single folder
##############################################################################################

if(is.local) {
  # Andy's setup for ag costs
  # df.tavg <- read.csv(tavgpath, skip=108) # skip=42, skip=108

  # Only pull the region, year, income, and irrigation columns.
  inc_irr.df <- read.csv(allcalcspath, skip=120, colClasses=c(NA, NA, rep('NULL', 94), NA, rep('NULL', 4), NA, rep('NULL', 15)))

  # Keep the order of the regions, but make each region run continuously in the df from 1981 - 2097
  # (As output, each region is 1981 - 2010 for all regions, then 2011 - 2097 for all regions.)
  ir_order <- unique(inc_irr.df$region)
  yr_order <- unique(inc_irr.df$year)
  ir_order <- rep(ir_order, each=length(unique(inc_irr.df$year)))
  yr_order <- rep(yr_order, length(unique(inc_irr.df$region)))

  # Following https://stackoverflow.com/questions/3990155/r-sort-multiple-columns-by-another-data-frame
  inc_irr.df <- inc_irr.df[ order(match(
    paste(inc_irr.df$region , inc_irr.df$year),
    paste(ir_order, yr_order)
  )), ]

  # Convert this to an array, to match the netcdf files, which are IR x year form.
  inc.array <- t( array( data = inc_irr.df$loggdppc,
                      dim = c(
                        length(unique(inc_irr.df$year)),
                        length(unique(inc_irr.df$region))),
                      dimnames = list(unique(inc_irr.df$year), unique(inc_irr.df$region))))

  irr.array <- t( array( data = inc_irr.df$ir.share,
                         dim = c(
                           length(unique(inc_irr.df$year)),
                           length(unique(inc_irr.df$region))),
                         dimnames = list(unique(inc_irr.df$year), unique(inc_irr.df$region))))


} else {

  # Read in income and irrigation netcdfs
  nc.inc <- nc_open(incpath)
  inc.array <- ncvar_get(nc.inc, 'loggdppc')
  nc.irr <- nc_open(irrpath)
  irr.array <- ncvar_get(nc.irr, 'irrigation')

  rownames(inc.array) <- ncvar_get(nc.inc, 'regions')
  colnames(inc.array) <- ncvar_get(nc.inc, 'year')
  rownames(irr.array) <- ncvar_get(nc.irr, 'regions')
  colnames(irr.array) <- ncvar_get(nc.irr, 'year')

}



## Open the weather and climate netcdfs
# Note: winter wheat has a separate data structure for weather data, but not for covariates (including climate covariates).
nc.tavg <- nc_open(tavgpath)
nc.pavg <- nc_open(pavgpath)
temps.avg <- ncvar_get(nc.tavg, 'averaged') #average temperatures
prcps.avg <- ncvar_get(nc.pavg, 'averaged') #average temperatures
regions.tavg <- ncvar_get(nc.tavg, 'regions')
regions.pavg <- ncvar_get(nc.pavg, 'regions')
year.tavg <- ncvar_get(nc.tavg, 'year')
year.pavg <- ncvar_get(nc.pavg, 'year')

if (crop != 'wheat-winter') {
  # Winter wheat has a separate weather data structure.
  # Load weather terms for non-winter-wheat crops. They are created with the average temps and have the same region and year indexing. 
  # Only include tmin if the crop is rice or spring wheat.
  nc.dd <- nc_open(ddpath)
  nc.pr <- nc_open(prpath)
  dd.yr <- ncvar_get(nc.dd, 'annual') # 'annual' 'averaged'
  pr.yr <- ncvar_get(nc.pr, 'annual') # 'annual' 'averaged'
  
  if ((crop == 'rice') | (crop == 'wheat-spring')) {
    if(!exclude.rice.tmin.costs) {
      nc.tmin <- nc_open(tminpath)
      tmin.yr <- ncvar_get(nc.tmin, 'annual') # 'annual' 'averaged'
      year.tmin <- ncvar_get(nc.tmin, 'year')
      regions.tmin <- ncvar_get(nc.tmin, 'regions')
    } else {
      tmin.yr <- dd.yr[1,,] * 0
      year.tmin <- year.tavg
      regions.tmin <- regions.tavg
    }
  } else {
    # Other crops don't use tmin, so set it to an array of zeros and it will drop out everywhere.
    tmin.yr <- dd.yr[1,,] * 0
    year.tmin <- ncvar_get(nc.tavg, 'year')
    regions.tmin <- ncvar_get(nc.tavg, 'regions')
  }
  
} else {
  # The crop is winter wheat. Winter wheat has a separate weather data structure due to fall/winter/summer seasons.
  # For winter wheat, the season without a season name appended (to mirror other crops) is spring/summer.
  nc.dd.fall <- nc_open(ddpath.fall)
  nc.dd.wint <- nc_open(ddpath.wint)
  nc.dd <- nc_open(ddpath)
  nc.pr.fall <- nc_open(prpath.fall)
  nc.pr.wint <- nc_open(prpath.wint)
  nc.pr <- nc_open(prpath)
  dd.yr.fall <- ncvar_get(nc.dd.fall, 'annual') # 'annual' 'averaged'
  dd.yr.wint <- ncvar_get(nc.dd.wint, 'annual') # 'annual' 'averaged'
  dd.yr <- ncvar_get(nc.dd, 'annual') # 'annual' 'averaged'
  pr.yr.fall <- ncvar_get(nc.pr.fall, 'annual') # 'annual' 'averaged'
  pr.yr.wint <- ncvar_get(nc.pr.wint, 'annual') # 'annual' 'averaged'
  pr.yr <- ncvar_get(nc.pr, 'annual') # 'annual' 'averaged'
  
  nc.tmin.wint <- nc_open(tminpath.wint)
  nc.tmin <- nc_open(tminpath)
  tmin.yr.wint <- ncvar_get(nc.tmin.wint, 'annual') # 'annual' 'averaged'
  tmin.yr <- ncvar_get(nc.tmin, 'annual') # 'annual' 'averaged'
  year.tmin <- ncvar_get(nc.tmin, 'year')
  regions.tmin <- ncvar_get(nc.tmin, 'regions')
}



## Data Validation
# Make sure indexing is consistent between pavg and tavg
if ( isTRUE(all.equal(year.pavg, year.tavg)) ) {
  year.avg <- year.tavg
  rm(year.tavg, year.pavg)

  # Match the length of the climate data (years) to the length of the projections (income covariate data)
  year.avg <- year.avg[ year.avg %in% colnames(inc.array) ]
  temps.avg <- temps.avg[, 1:length(year.avg)][, 1:length(year.avg)]
  prcps.avg <- prcps.avg[, 1:length(year.avg)][, 1:length(year.avg)]


} else {
  stop(paste0('Year indexing is inconsistent between tavg and pavg data. File paths: \n', tavgpath, '\n', pavgpath))
}

# Make sure tmin year indexing is consistent and not longer than projections.
if ( isTRUE(all.equal(year.avg, year.tmin)) ) {
  rm(year.tmin)
} else {
  stop(paste0('Year indexing for tmin is inconsistent or too long.'))
}

if ( isTRUE(all.equal(regions.pavg, regions.tavg)) ) {
  regions <- regions.tavg
  rm(regions.tavg, regions.pavg)
} else {
  stop(paste0('Region indexing is inconsistent between tavg and pavg data. File paths: \n', tavgpath, '\n', pavgpath))
}

# Make sure tmin region indexing is also consistent
if ( isTRUE(all.equal(regions, regions.tmin)) ) {
  rm(regions.tmin)
} else {
  stop(paste0('Region indexing for tmin is inconsistent.'))
}


if (!isTRUE(all.equal(as.character(regions), as.character(rownames(inc.array))))) {
  stop(paste0('Region indexing is inconsistent between climate data and income data. File paths: \n', tavgpath, '\n', incpath))
}



## Set up covariate expected values.
# We use lagged covariates for expectations, so just lag temps.avg and prcps.avg now
tmp <- array(NA, dim=c(dim(temps.avg)[1],1))
temps.avg.lag <- abind(tmp, temps.avg, along=2)
temps.avg.lag <- temps.avg.lag[ , 1:(dim(temps.avg.lag)[2]-1) ]

tmp <- array(NA, dim=c(dim(prcps.avg)[1],1))
prcps.avg.lag <- abind(tmp, prcps.avg, along=2)
prcps.avg.lag <- prcps.avg.lag[ , 1:(dim(prcps.avg.lag)[2]-1) ]

tmp <- array(NA, dim=c(dim(temps.avg)[1],1))
inc.array.lag <- abind(tmp, inc.array, along=2)
inc.array.lag <- inc.array.lag[ , 1:(dim(inc.array.lag)[2]-1) ]

temps.avg <- temps.avg.lag
prcps.avg <- prcps.avg.lag
inc.array <- inc.array.lag
rm(temps.avg.lag, prcps.avg.lag, inc.array.lag)

# We use 2015 values of covariates for all years before 2015.
# For each IR (row), replace the climate covariate value with the 2015 value for
# all years before 2015.
ones.v <- rep(1, dim(prcps.avg[,1:35])[2])
temps.avg[, 1:35] <- temps.avg[, 35] %*% t(ones.v)
prcps.avg[, 1:35] <- prcps.avg[, 35] %*% t(ones.v)
inc.array[, 1:35] <- inc.array[, 35] %*% t(ones.v)

# Impose pbar spline for gdds and kdds and (for rice and wheat) tmin. And pr, will need it later. 
# And assign 2015 values to pre-2015 period.
prcps.avg.gdd.spline <- prcps.avg * (prcps.avg < pbar.kink.gdd) + pbar.kink.gdd * (prcps.avg >= pbar.kink.gdd)
prcps.avg.kdd.spline <- prcps.avg * (prcps.avg < pbar.kink.kdd) + pbar.kink.kdd * (prcps.avg >= pbar.kink.kdd)
prcps.avg.pr.spline <- prcps.avg * (prcps.avg < pbar.kink.pr) + pbar.kink.pr * (prcps.avg >= pbar.kink.pr)

prcps.avg.gdd.spline[, 1:35] <- prcps.avg.gdd.spline[, 35] %*% t(ones.v)
prcps.avg.kdd.spline[, 1:35] <- prcps.avg.kdd.spline[, 35] %*% t(ones.v)
prcps.avg.pr.spline[, 1:35] <- prcps.avg.pr.spline[, 35] %*% t(ones.v)

if ((crop=='rice') | (crop == 'wheat-spring') | (crop == 'wheat-winter')) {
  prcps.avg.tmin.spline <- prcps.avg * (prcps.avg < pbar.kink.tmin) + pbar.kink.tmin * (prcps.avg >= pbar.kink.tmin)
  prcps.avg.tmin.spline[, 1:35] <- prcps.avg.tmin.spline[, 35] %*% t(ones.v)
  
  if (crop == 'wheat-winter') {
    # Winter wheat has a separate pbar-spline for winter season tmin.
    prcps.avg.tmin.spline.wint <- prcps.avg * (prcps.avg < pbar.kink.tmin.wint) + pbar.kink.tmin.wint * (prcps.avg >= pbar.kink.tmin.wint)
    prcps.avg.tmin.spline.wint[, 1:35] <- prcps.avg.tmin.spline.wint[, 35] %*% t(ones.v)
  }
}





##############################################################################################
# Calculate adaptation terms for each region-year. This calculation is memory-intensive in the
# projection system, so for ag we are moving it to this script, for efficiency.
##############################################################################################



# Read in the regression coefficients from the .csvv file and grab three rows:
# The row of predictor names, the row of covariate names, and the row of coefficient values.
coeffs <- read.csv(gammapath, skip=csvv.skip.lines, header=FALSE, stringsAsFactors=FALSE)

if(seed!='') {
  # If <seed> is not '', then this script is being used to replicate a Monte Carlo coefficient draw from the
  # variance covariance matrix. In this case, <seed> must be a numeric value. The Monte Carlos are
  # implemented in python, and so the draw must be replicated in python as well.
  # Note: the last two rows of the csvv give the std. error of the residuals and are not part of the vcv.
  vcv.rows <- 7:(dim(coeffs)[1]-2)
  coeffs.vcv <- as.matrix(coeffs[vcv.rows,])

  # Replicate the Monte Carlo draw (in Python) from the variance covariance matrix.
  # See this git issue: https://gitlab.com/ClimateImpactLab/Impacts/impact-calculations/-/issues/132
  #scipy.stats <- import('scipy.stats')
  np <- import('numpy')
  # pd <- import('pandas')
  
  # Attempt 1 -- this is the original approach in the projection system, but unfortunately is unstable for some VCVs
  # np$random$seed(as.integer(seed))
  # coeffs.draw <- scipy.stats$multivariate_normal$rvs(as.numeric(coeffs[5,]), coeffs.vcv)
  
  # Attempt 2 -- this is a change to the unstable approach above, which fixed some things but not the instability.
  # rng <- np$random$default_rng(as.integer(seed))
  # coeffs.draw <- scipy.stats$multivariate_normal$rvs(as.numeric(coeffs[5,]), coeffs.vcv, random_state=rng)
  
  # Attempt 3 -- this fixes the instability, we believe.
  rng <- np$random$Generator(np$random$PCG64( as.integer(seed) ))
  coeffs.draw <- rng$multivariate_normal(
    mean=as.numeric(coeffs[5,]),
    cov=coeffs.vcv,
    check_valid="raise",
    method='eigh'
  )
  
  coeffs[5,] <- coeffs.draw
  
  # For passing particular MC coeff draws to Kit for diagnostics.
  # print(coeffs.draw)
  # stop()

}


coeffs <- coeffs [c(1,3,5),]

# Trim whitespace from predictor and covariate names
coeffs[1,] <- trimws(coeffs[1,])
coeffs[2,] <- trimws(coeffs[2,])


get.coeff <- function( clim, cov, csvv.df=coeffs, csvv.vcv=coeffs.vcv, seed=NA ) {
  # Given a .csvv file read in above from gammapath, find the coefficient corresponding to the
  # interaction between <clim> (the weather parameter) and <cov> (the covariate). For main effects
  # of the <clim> parameters, pass a string of '1' as the argument for <cov>.

  return(as.numeric( csvv.df[3, (csvv.df[1,] %in% clim) & (csvv.df[2,] %in% cov)] ))

}



# In every year-ir that is clipped, force the costs to be zero.
# Check for clipping in GDD (clip if GDD coeff < 0) and in KDD (clip if KDD coeff > 0).
# This filter takes a value of 1 when costs should be clipped. Apply it when calculating costs.
no_gdd_clip <- TRUE

if ((crop=='maize') | (crop=='soy') | (crop=='wheat-spring') | (crop=='wheat-winter')) {
  gdd.clip.filter <- ( 0 <
                         get.coeff(gdd_var,'1') +
                         get.coeff(gdd_var,'seasonaltasmax')*temps.avg +
                         get.coeff(gdd_var,'seasonalpr')*prcps.avg.gdd.spline +
                         get.coeff(gdd_var,'seasonaltasmax*seasonalpr')*temps.avg*prcps.avg.gdd.spline +
                         get.coeff(gdd_var,'loggdppc')*inc.array +
                         get.coeff(gdd_var,'ir-share')*irr.array
  )
  
  
  kdd.clip.filter <- ( 0 >
                         get.coeff(kdd_var,'1') +
                         get.coeff(kdd_var,'seasonaltasmax')*temps.avg +
                         get.coeff(kdd_var,'seasonalpr')*prcps.avg.kdd.spline +
                         get.coeff(kdd_var,'seasonaltasmax*seasonalpr')*temps.avg*prcps.avg.kdd.spline +
                         get.coeff(kdd_var,'loggdppc')*inc.array +
                         get.coeff(kdd_var,'ir-share')*irr.array
  )
  
  if (crop=='wheat-winter') {
    # Winter wheat needs fall and winter season gdd/kdd clip filters.
    
    gdd.clip.filter.fall <- ( 0 <
                           get.coeff(gdd_var.fall,'1') +
                           get.coeff(gdd_var.fall,'seasonaltasmax')*temps.avg +
                           get.coeff(gdd_var.fall,'seasonalpr')*prcps.avg.gdd.spline +
                           get.coeff(gdd_var.fall,'seasonaltasmax*seasonalpr')*temps.avg*prcps.avg.gdd.spline +
                           get.coeff(gdd_var.fall,'loggdppc')*inc.array +
                           get.coeff(gdd_var.fall,'ir-share')*irr.array
    )
    
    
    kdd.clip.filter.fall <- ( 0 >
                           get.coeff(kdd_var.fall,'1') +
                           get.coeff(kdd_var.fall,'seasonaltasmax')*temps.avg +
                           get.coeff(kdd_var.fall,'seasonalpr')*prcps.avg.kdd.spline +
                           get.coeff(kdd_var.fall,'seasonaltasmax*seasonalpr')*temps.avg*prcps.avg.kdd.spline +
                           get.coeff(kdd_var.fall,'loggdppc')*inc.array +
                           get.coeff(kdd_var.fall,'ir-share')*irr.array
    )
    
    gdd.clip.filter.wint <- ( 0 <
                                get.coeff(gdd_var.wint,'1') +
                                get.coeff(gdd_var.wint,'seasonaltasmax')*temps.avg +
                                get.coeff(gdd_var.wint,'seasonalpr')*prcps.avg.gdd.spline +
                                get.coeff(gdd_var.wint,'seasonaltasmax*seasonalpr')*temps.avg*prcps.avg.gdd.spline +
                                get.coeff(gdd_var.wint,'loggdppc')*inc.array +
                                get.coeff(gdd_var.wint,'ir-share')*irr.array
    )
    
    
    kdd.clip.filter.wint <- ( 0 >
                                get.coeff(kdd_var.wint,'1') +
                                get.coeff(kdd_var.wint,'seasonaltasmax')*temps.avg +
                                get.coeff(kdd_var.wint,'seasonalpr')*prcps.avg.kdd.spline +
                                get.coeff(kdd_var.wint,'seasonaltasmax*seasonalpr')*temps.avg*prcps.avg.kdd.spline +
                                get.coeff(kdd_var.wint,'loggdppc')*inc.array +
                                get.coeff(kdd_var.wint,'ir-share')*irr.array
    )
    
  }
} else if ((crop=='rice') | crop==('sorghum')) {
  gdd.clip.filter <- ( 0 <
                         get.coeff(gdd_var,'1') +
                         get.coeff(gdd_var,'seasonaltasmax')*temps.avg +
                         get.coeff(gdd_var,'seasonalpr')*prcps.avg.gdd.spline +
                         get.coeff(gdd_var,'loggdppc')*inc.array +
                         get.coeff(gdd_var,'ir-share')*irr.array
  )
  
  
  kdd.clip.filter <- ( 0 >
                         get.coeff(kdd_var,'1') +
                         get.coeff(kdd_var,'seasonaltasmax')*temps.avg +
                         get.coeff(kdd_var,'seasonalpr')*prcps.avg.kdd.spline +
                         get.coeff(kdd_var,'loggdppc')*inc.array +
                         get.coeff(kdd_var,'ir-share')*irr.array
  ) 
} else if (crop=='cassava') {
  gdd.clip.filter <- ( 0 <
                         get.coeff(gdd_var,'1') +
                         get.coeff(gdd_var,'seasonaltasmax')*temps.avg +
                         get.coeff(gdd_var,'seasonalpr')*prcps.avg.gdd.spline +
                         get.coeff(gdd_var,'loggdppc')*inc.array
  )
  
  
  kdd.clip.filter <- ( 0 >
                         get.coeff(kdd_var,'1') +
                         get.coeff(kdd_var,'seasonaltasmax')*temps.avg +
                         get.coeff(kdd_var,'seasonalpr')*prcps.avg.kdd.spline +
                         get.coeff(kdd_var,'loggdppc')*inc.array
  ) 
} else {
  print('This crop is not yet configured.')
  stop()
}



if(no_gdd_clip) {
  gdd.clip.filter <- gdd.clip.filter*0 + 1
  # Set NA values
  gdd.clip.filter[is.na(gdd.clip.filter)] <- 1
  kdd.clip.filter[is.na(kdd.clip.filter)] <- 0
  
  if(crop=='wheat-winter') {
    gdd.clip.filter.fall <- gdd.clip.filter.fall*0 + 1
    gdd.clip.filter.wint <- gdd.clip.filter.wint*0 + 1
    # Set NA values
    gdd.clip.filter.fall[is.na(gdd.clip.filter.fall)] <- 1
    kdd.clip.filter.fall[is.na(kdd.clip.filter.fall)] <- 0
    gdd.clip.filter.wint[is.na(gdd.clip.filter.wint)] <- 1
    kdd.clip.filter.wint[is.na(kdd.clip.filter.wint)] <- 0
  }
  

} else {
  # Set NA values to zero
  gdd.clip.filter[is.na(gdd.clip.filter)] <- 0
  kdd.clip.filter[is.na(kdd.clip.filter)] <- 0
  
  if(crop=='wheat-winter') {
    gdd.clip.filter.fall[is.na(gdd.clip.filter.fall)] <- 0
    kdd.clip.filter.fall[is.na(kdd.clip.filter.fall)] <- 0
    gdd.clip.filter.wint[is.na(gdd.clip.filter.wint)] <- 0
    kdd.clip.filter.wint[is.na(kdd.clip.filter.wint)] <- 0
  }
  
}



#print('Precip data dimensions are:')
#print(dim(pr.yr))



### Compute marginals terms
# Maize, soy, and both wheats have Tbar x Pbar covariate interactions
# Rice, cassava, and sorghum do not

# Winter wheat marginals terms are structured differently, due to separate structure of the weather data. Remember, winter wheat
# weather data has a season identifier appended for fall and winter, but not summer (so that one season's names -- summer -- are 
# similar to other crops).  E.g. dd.yr is summer degree days, while dd.yr.fall is fall, and dd.yr.wint is winter.

# For use of `if`() as a ternary operator which can take scalar input and give matrix output, see https://stackoverflow.com/a/48890803

# Initialize a zeros matrix matching the dimensions of the data, for adding zeros when interaction terms are not present for a crop.
zeros.mat <- dd.yr[1,,] * 0


## d(y_gdd)/d(Tbar) + d(y_kdd)/d(Tbar)

marginal.tbar.temp <- ( dd.yr[1,,] * gdd.clip.filter *
                        ( get.coeff(gdd_var,'seasonaltasmax') + `if`(has.TxP,
                                                                     get.coeff(gdd_var,'seasonaltasmax*seasonalpr')*prcps.avg.gdd.spline, zeros.mat) ) +
                        dd.yr[2,,] * kdd.clip.filter *
                        ( get.coeff(kdd_var,'seasonaltasmax') + `if`(has.TxP,
                                                                     get.coeff(kdd_var,'seasonaltasmax*seasonalpr')*prcps.avg.kdd.spline, zeros.mat) )
)

if (crop == 'wheat-winter') {
  # Add marginals terms for the fall and winter seasons.
  marginal.tbar.temp <- marginal.tbar.temp +
                        # Fall
                        ( dd.yr.fall[1,,] * gdd.clip.filter.fall *
                            ( get.coeff(gdd_var.fall,'seasonaltasmax') + `if`(has.TxP,
                                                                         get.coeff(gdd_var.fall,'seasonaltasmax*seasonalpr')*prcps.avg.gdd.spline, zeros.mat) ) +
                            dd.yr.fall[2,,] * kdd.clip.filter.fall *
                            ( get.coeff(kdd_var.fall,'seasonaltasmax') + `if`(has.TxP,
                                                                         get.coeff(kdd_var.fall,'seasonaltasmax*seasonalpr')*prcps.avg.kdd.spline, zeros.mat) ) 
  ) +
                        # Winter
                        ( dd.yr.wint[1,,] * gdd.clip.filter.wint *
                            ( get.coeff(gdd_var.wint,'seasonaltasmax') + `if`(has.TxP,
                                                                              get.coeff(gdd_var.wint,'seasonaltasmax*seasonalpr')*prcps.avg.gdd.spline, zeros.mat) ) +
                            dd.yr.wint[2,,] * kdd.clip.filter.wint *
                            ( get.coeff(kdd_var.wint,'seasonaltasmax') + `if`(has.TxP,
                                                                              get.coeff(kdd_var.wint,'seasonaltasmax*seasonalpr')*prcps.avg.kdd.spline, zeros.mat) )  
  )
}


# print('diagnostics')
# print(dim(dd.yr))
# print(dim(gdd.clip.filter))
# print(dim(kdd.clip.filter))
# print(dim(prcps.avg.gdd.spline))
# print(get.coeff(gdd_var,'seasonaltasmax'))
# print(dim(marginal.tbar.temp))
# print(get.coeff(pr_var.bin1,'seasonaltasmax'))

## d(y_pr)/d(Tbar)

if ((crop != 'cassava') & (crop != 'wheat-spring') & (crop != 'wheat-winter')) {
  # Cassava and spring wheat do not have different prcp responses over the growing season. Winter wheat data is structured differently. 
  # All other crops do have different prcp responses, where the precip response differs by "month-bins" (groupings of months).
  
  # Maize month-bins are months 1, 2-4, 5+
  marginal.tbar.prcp <- (
    # Month-bin 1 (for maize, this is month 1)
    pr.yr[1,,] *
      ( get.coeff(pr_var.bin1,'seasonaltasmax') + `if`(has.TxP,
                                                       get.coeff(pr_var.bin1,'seasonaltasmax*seasonalpr')*prcps.avg.pr.spline, zeros.mat) ) +
      pr.yr[2,,] *
      ( get.coeff(pr2_var.bin1,'seasonaltasmax') + `if`(has.TxP,
                                                        get.coeff(pr2_var.bin1,'seasonaltasmax*seasonalpr')*prcps.avg.pr.spline, zeros.mat) ) +
      
      # Month-bin 2 (for maize, this is months 2-4)
      pr.yr[3,,] *
      ( get.coeff(pr_var.bin2,'seasonaltasmax') + `if`(has.TxP,
                                                       get.coeff(pr_var.bin2,'seasonaltasmax*seasonalpr')*prcps.avg.pr.spline, zeros.mat) ) +
      pr.yr[4,,] *
      ( get.coeff(pr2_var.bin2,'seasonaltasmax') + `if`(has.TxP,
                                                        get.coeff(pr2_var.bin2,'seasonaltasmax*seasonalpr')*prcps.avg.pr.spline, zeros.mat) ) +
      
      # Month-bin 3 (for maize, this is months 5+)
      pr.yr[5,,] *
      ( get.coeff(pr_var.bin3,'seasonaltasmax') + `if`(has.TxP,
                                                       get.coeff(pr_var.bin3,'seasonaltasmax*seasonalpr')*prcps.avg.pr.spline, zeros.mat) ) +
      pr.yr[6,,] *
      ( get.coeff(pr2_var.bin3,'seasonaltasmax') + `if`(has.TxP,
                                                        get.coeff(pr2_var.bin3,'seasonaltasmax*seasonalpr')*prcps.avg.pr.spline, zeros.mat) )
  )
  
  if( (crop=='soy') ) {
    
    # Soy has four month-bins, not three
    marginal.tbar.prcp <- marginal.tbar.prcp +
      pr.yr[7,,] *
      ( get.coeff(pr_var.bin4,'seasonaltasmax') + `if`(has.TxP,
                                                       get.coeff(pr_var.bin4,'seasonaltasmax*seasonalpr')*prcps.avg.pr.spline, zeros.mat) ) +
      pr.yr[8,,] *
      ( get.coeff(pr2_var.bin4,'seasonaltasmax') + `if`(has.TxP,
                                                        get.coeff(pr2_var.bin4,'seasonaltasmax*seasonalpr')*prcps.avg.pr.spline, zeros.mat) )
    
  }

} else {

  # Cassava and spring wheat, and winter wheat summer season
  marginal.tbar.prcp <- ( pr.yr[1,,] * ( get.coeff(pr_var.bin1,'seasonaltasmax') + 
                                         `if`(has.TxP, get.coeff(pr_var.bin1,'seasonaltasmax*seasonalpr')*prcps.avg.pr.spline, zeros.mat) )
    ) +
    ( pr.yr[2,,] * ( get.coeff(pr2_var.bin1,'seasonaltasmax') + 
                       `if`(has.TxP, get.coeff(pr2_var.bin1,'seasonaltasmax*seasonalpr')*prcps.avg.pr.spline, zeros.mat) )
    )
  
 
  if ((crop == 'wheat-spring') | (crop == 'wheat-winter')) {
    # Spring and winter wheat have 4th order prcp polynomials, so two more terms than the quadratic for cassava.
    marginal.tbar.prcp <- marginal.tbar.prcp +
      ( pr.yr[3,,] * ( get.coeff(pr3_var.bin1,'seasonaltasmax') + 
                         `if`(has.TxP, get.coeff(pr3_var.bin1,'seasonaltasmax*seasonalpr')*prcps.avg.pr.spline, zeros.mat) )
      ) +
      ( pr.yr[4,,] * ( get.coeff(pr4_var.bin1,'seasonaltasmax') + 
                         `if`(has.TxP, get.coeff(pr4_var.bin1,'seasonaltasmax*seasonalpr')*prcps.avg.pr.spline, zeros.mat) )
      )
  }
  
  if (crop == 'wheat-winter') {
    # Fall and winter for winter wheat
    marginal.tbar.prcp <- marginal.tbar.prcp +
    
      # Fall
      ( pr.yr.fall[1,,] * ( get.coeff(pr_var.bin1.fall,'seasonaltasmax') + 
                                             `if`(has.TxP, get.coeff(pr_var.bin1.fall,'seasonaltasmax*seasonalpr')*prcps.avg.pr.spline, zeros.mat) )
      ) +
      ( pr.yr.fall[2,,] * ( get.coeff(pr2_var.bin1.fall,'seasonaltasmax') + 
                              `if`(has.TxP, get.coeff(pr2_var.bin1.fall,'seasonaltasmax*seasonalpr')*prcps.avg.pr.spline, zeros.mat) )
      ) +
      ( pr.yr.fall[3,,] * ( get.coeff(pr3_var.bin1.fall,'seasonaltasmax') + 
                              `if`(has.TxP, get.coeff(pr3_var.bin1.fall,'seasonaltasmax*seasonalpr')*prcps.avg.pr.spline, zeros.mat) )
      ) +
      ( pr.yr.fall[4,,] * ( get.coeff(pr4_var.bin1.fall,'seasonaltasmax') + 
                              `if`(has.TxP, get.coeff(pr4_var.bin1.fall,'seasonaltasmax*seasonalpr')*prcps.avg.pr.spline, zeros.mat) )
      ) +
      
      # Winter
      ( pr.yr.wint[1,,] * ( get.coeff(pr_var.bin1.wint,'seasonaltasmax') + 
                         `if`(has.TxP, get.coeff(pr_var.bin1.wint,'seasonaltasmax*seasonalpr')*prcps.avg.pr.spline, zeros.mat) )
      ) +
      ( pr.yr.wint[2,,] * ( get.coeff(pr2_var.bin1.wint,'seasonaltasmax') + 
                              `if`(has.TxP, get.coeff(pr2_var.bin1.wint,'seasonaltasmax*seasonalpr')*prcps.avg.pr.spline, zeros.mat) )
      ) +
      ( pr.yr.wint[3,,] * ( get.coeff(pr3_var.bin1.wint,'seasonaltasmax') + 
                              `if`(has.TxP, get.coeff(pr3_var.bin1.wint,'seasonaltasmax*seasonalpr')*prcps.avg.pr.spline, zeros.mat) )
      ) +
      ( pr.yr.wint[4,,] * ( get.coeff(pr4_var.bin1.wint,'seasonaltasmax') + 
                              `if`(has.TxP, get.coeff(pr4_var.bin1.wint,'seasonaltasmax*seasonalpr')*prcps.avg.pr.spline, zeros.mat) )
      ) 
  }
  
}



## d(y_gdd)/d(Pbar) + d(y_kdd)/d(Pbar)

marginal.pbar.temp <- ( dd.yr[1,,] * gdd.clip.filter *
                        ( get.coeff(gdd_var,'seasonalpr') + `if`(has.TxP, 
                                                                 get.coeff(gdd_var,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) ) * (prcps.avg<pbar.kink.gdd) +
                        dd.yr[2,,] * kdd.clip.filter *
                        ( get.coeff(kdd_var,'seasonalpr') + `if`(has.TxP, 
                                                                 get.coeff(kdd_var,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) ) * (prcps.avg<pbar.kink.kdd)
)

if (crop == 'wheat-winter') {
  # Fall and winter for winter wheat
  marginal.pbar.temp <- marginal.pbar.temp +
                        # Fall
                        ( dd.yr.fall[1,,] * gdd.clip.filter.fall *
                            ( get.coeff(gdd_var.fall,'seasonalpr') + `if`(has.TxP, 
                                                                     get.coeff(gdd_var.fall,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) ) * (prcps.avg<pbar.kink.gdd) +
                            dd.yr.fall[2,,] * kdd.clip.filter.fall *
                            ( get.coeff(kdd_var.fall,'seasonalpr') + `if`(has.TxP, 
                                                                     get.coeff(kdd_var.fall,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) ) * (prcps.avg<pbar.kink.kdd)
                        ) +
                        # Winter
                        ( dd.yr.wint[1,,] * gdd.clip.filter.wint *
                            ( get.coeff(gdd_var.wint,'seasonalpr') + `if`(has.TxP, 
                                                                          get.coeff(gdd_var.wint,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) ) * (prcps.avg<pbar.kink.gdd) +
                            dd.yr.wint[2,,] * kdd.clip.filter.wint *
                            ( get.coeff(kdd_var.wint,'seasonalpr') + `if`(has.TxP, 
                                                                          get.coeff(kdd_var.wint,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) ) * (prcps.avg<pbar.kink.kdd)
                        )
}

## d(y_pr)/d(Pbar)

if ((crop != 'cassava') & (crop != 'wheat-spring') & (crop != 'wheat-winter')) {
  # Cassava and spring wheat do not have different prcp responses over the growing season. Winter wheat data is structured differently.
  # All other crops do have different prcp responses, where the precip response differs by "month-bins" (groupings of months).
  marginal.pbar.prcp <- (
                          # Month 1
                          pr.yr[1,,] *
                          ( get.coeff(pr_var.bin1,'seasonalpr') + `if`(has.TxP,
                                                                       get.coeff(pr_var.bin1,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) ) +
                          pr.yr[2,,] *
                          ( get.coeff(pr2_var.bin1,'seasonalpr') + `if`(has.TxP,
                                                                        get.coeff(pr2_var.bin1,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) ) +
  
                          # Months 2-4
                          pr.yr[3,,] *
                          ( get.coeff(pr_var.bin2,'seasonalpr') + `if`(has.TxP,
                                                                       get.coeff(pr_var.bin2,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) ) +
                          pr.yr[4,,] *
                          ( get.coeff(pr2_var.bin2,'seasonalpr') + `if`(has.TxP,
                                                                        get.coeff(pr2_var.bin2,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) ) +
  
                          # Months 5+
                          pr.yr[5,,] *
                          ( get.coeff(pr_var.bin3,'seasonalpr') + `if`(has.TxP,
                                                                       get.coeff(pr_var.bin3,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) ) +
                          pr.yr[6,,] *
                          ( get.coeff(pr2_var.bin3,'seasonalpr') + `if`(has.TxP,
                                                                        get.coeff(pr2_var.bin3,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) )
  ) * (prcps.avg<pbar.kink.pr)
  
  if(crop=='soy') {
  
    marginal.pbar.prcp <- marginal.pbar.prcp +
                          (
                          pr.yr[7,,] *
                          ( get.coeff(pr_var.bin4,'seasonalpr') + `if`(has.TxP,
                                                                       get.coeff(pr_var.bin4,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) ) +
                          pr.yr[8,,] *
                          ( get.coeff(pr2_var.bin4,'seasonalpr') + `if`(has.TxP,
                                                                        get.coeff(pr2_var.bin4,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) )
    ) * (prcps.avg<pbar.kink.pr)
  
  }
} else {
  
  # Cassava and spring wheat and, winter wheat summer season
  marginal.pbar.prcp <- ( pr.yr[1,,] * ( get.coeff(pr_var.bin1,'seasonalpr') + 
                                         `if`(has.TxP, get.coeff(pr_var.bin1,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) ) +
                          pr.yr[2,,] * ( get.coeff(pr2_var.bin1,'seasonalpr') + 
                                          `if`(has.TxP, get.coeff(pr2_var.bin1,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) )
  ) * (prcps.avg<pbar.kink.pr)
  
  # Spring and winter wheat are 4th order prcp polynomials, add those terms (winter wheat summer season).
  if ((crop == 'wheat-spring') | (crop == 'wheat-winter')) {
    marginal.pbar.prcp <- marginal.pbar.prcp +
      ( pr.yr[3,,] * ( get.coeff(pr3_var.bin1,'seasonalpr') + 
                         `if`(has.TxP, get.coeff(pr3_var.bin1,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) ) +
        pr.yr[4,,] * ( get.coeff(pr4_var.bin1,'seasonalpr') + 
                           `if`(has.TxP, get.coeff(pr4_var.bin1,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) )
      ) * (prcps.avg<pbar.kink.pr)
  }
    
  
  if (crop == 'wheat-winter') {
    # Fall and winter for winter wheat
    marginal.pbar.prcp <- marginal.pbar.prcp +
      
      # Fall
      ( pr.yr.fall[1,,] * ( get.coeff(pr_var.bin1.fall,'seasonalpr') + 
                         `if`(has.TxP, get.coeff(pr_var.bin1.fall,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) ) +
        pr.yr.fall[2,,] * ( get.coeff(pr2_var.bin1.fall,'seasonalpr') + 
                         `if`(has.TxP, get.coeff(pr2_var.bin1.fall,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) ) +
        pr.yr.fall[3,,] * ( get.coeff(pr3_var.bin1.fall,'seasonalpr') + 
                         `if`(has.TxP, get.coeff(pr3_var.bin1.fall,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) ) +
        pr.yr.fall[4,,] * ( get.coeff(pr4_var.bin1.fall,'seasonalpr') + 
                         `if`(has.TxP, get.coeff(pr4_var.bin1.fall,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) )
      ) * (prcps.avg<pbar.kink.pr) +
      
      # Winter
      ( pr.yr.wint[1,,] * ( get.coeff(pr_var.bin1.wint,'seasonalpr') + 
                         `if`(has.TxP, get.coeff(pr_var.bin1.wint,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) ) +
        pr.yr.wint[2,,] * ( get.coeff(pr2_var.bin1.wint,'seasonalpr') + 
                         `if`(has.TxP, get.coeff(pr2_var.bin1.wint,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) ) +
        pr.yr.wint[3,,] * ( get.coeff(pr3_var.bin1.wint,'seasonalpr') + 
                         `if`(has.TxP, get.coeff(pr3_var.bin1.wint,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) ) +
        pr.yr.wint[4,,] * ( get.coeff(pr4_var.bin1.wint,'seasonalpr') + 
                         `if`(has.TxP, get.coeff(pr4_var.bin1.wint,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) ) 
      ) * (prcps.avg<pbar.kink.pr)
  }
  
}


## d(y_tmin)/d(Tbar) & d(y_tmin)/d(Pbar)
# Only for rice and wheat, set to zero otherwise.

if ((crop == 'rice') | (crop == 'wheat-spring') | (crop == 'wheat-winter')) {

  marginal.tbar.tmin <- ( tmin.yr  *
                          ( get.coeff(tmin_var,'seasonaltasmax') + `if`(has.TxP,
                                                                        get.coeff(tmin_var,'seasonaltasmax*seasonalpr')*prcps.avg.tmin.spline, zeros.mat) )
                        )

  marginal.pbar.tmin <- ( tmin.yr *
                            ( get.coeff(tmin_var,'seasonalpr') + `if`(has.TxP,
                                                                      get.coeff(tmin_var,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) ) * (prcps.avg<pbar.kink.tmin)
                        )
  
  if (crop == 'wheat-winter'){ 
    # Winter season tmin components for winter wheat
    
    marginal.tbar.tmin <- marginal.tbar.tmin + 
                          ( tmin.yr.wint  *
                              ( get.coeff(tmin_var.wint,'seasonaltasmax') + `if`(has.TxP,
                                                                            get.coeff(tmin_var.wint,'seasonaltasmax*seasonalpr')*prcps.avg.tmin.spline.wint, zeros.mat) )
    )
    
    marginal.pbar.tmin <- marginal.pbar.tmin + 
                          ( tmin.yr.wint *
                              ( get.coeff(tmin_var.wint,'seasonalpr') + `if`(has.TxP,
                                                                        get.coeff(tmin_var.wint,'seasonaltasmax*seasonalpr')*temps.avg, zeros.mat) ) * (prcps.avg<pbar.kink.tmin.wint)
    )
    
    
  }

  # Diagnostics
  if (1==0) {
    print('##### COSTS DIAGNOSTICS ####')
    print('Dim, marginal.tbar.tmin, marginal.pbar.tmin, dim(marginal.tbar.temp), marginal.tbar.temp')
    print(dim(marginal.tbar.tmin))
    print(marginal.tbar.tmin[1:5,1:5])
    print(marginal.pbar.tmin[1:5,1:5])
    print(dim(marginal.tbar.temp))
    print(marginal.tbar.temp[1:5,1:5])
    print(class(marginal.tbar.temp))
    print(class(marginal.tbar.tmin))
    print(class(marginal.pbar.tmin))
    
    yr.idx <- 108:112
        
    my.ir <- 'IND.31.483.1960'
    my.idx <- which(regions==my.ir)
    # print(regions[my.idx])
    print('##########')
    print(paste0('Diagnostics for region ', my.ir))
    print(year.avg[yr.idx])
    print('marginal.tbar.(temp,prcp,tmin), margina.pbar.(temp.prcp,tmin)')
    print('##########')
    print(marginal.tbar.temp[my.idx,yr.idx])
    print(marginal.tbar.prcp[my.idx,yr.idx])
    print(marginal.tbar.tmin[my.idx,yr.idx])
    print(marginal.pbar.temp[my.idx,yr.idx])
    print(marginal.pbar.prcp[my.idx,yr.idx])
    print(marginal.pbar.tmin[my.idx,yr.idx])
    print('##########')
    print('##########')
    my.ir <- 'IND.31.477.1929' # 'IND.31.483.1960'
    my.idx <- which(regions==my.ir)
    print(my.idx)
    print(paste0('Diagnostics for region ', my.ir))
    print(year.avg[yr.idx])
    print('marginal.tbar.(temp,prcp,tmin), margina.pbar.(temp.prcp,tmin)')
    print('##########')
    print(marginal.tbar.temp[my.idx,yr.idx])
    print(marginal.tbar.prcp[my.idx,yr.idx])
    print(marginal.tbar.tmin[my.idx,yr.idx])
    print(marginal.pbar.temp[my.idx,yr.idx])
    print(marginal.pbar.prcp[my.idx,yr.idx])
    print(marginal.pbar.tmin[my.idx,yr.idx])
    
    print('weather data: tmin, tmin_winter, gdd_winter, kdd_winter')
    print(tmin.yr[my.idx,yr.idx])
    print(tmin.yr.wint[my.idx,yr.idx])
    print(dd.yr.wint[1,my.idx,yr.idx])
    print(dd.yr.wint[2,my.idx,yr.idx])
    
    print('##')
    print('Specific Winter GDD / Tbar diagnostics')
    print('##')
    
    print(dd.yr.wint[1,my.idx,yr.idx])
    print(gdd.clip.filter.wint[my.idx,yr.idx])
    print(get.coeff(gdd_var.wint,'seasonaltasmax'))
    print(get.coeff(gdd_var.wint,'seasonaltasmax*seasonalpr'))
    print(prcps.avg.gdd.spline[my.idx,yr.idx])
    print(prcps.avg[my.idx,yr.idx])
    print(temps.avg[my.idx,yr.idx])
    

    tmp <- dd.yr.wint[1,,] * gdd.clip.filter.wint *
      ( get.coeff(gdd_var.wint,'seasonaltasmax') + `if`(has.TxP,
                                                        get.coeff(gdd_var.wint,'seasonaltasmax*seasonalpr')*prcps.avg.gdd.spline, zeros.mat) )

    print(tmp[my.idx,yr.idx])
    
    
    
    # print('Some nearby regions')
    # print(regions[3196:3200])
    # print(dd.yr.wint[1,3196:3200,yr.idx])
    # print(dd.yr.wint[1,3196:3200,1:5])
    # print('#')
    # print(dd.yr.wint[1,3196:3200,])
    # print('#')
    # print(dd.yr.wint[2,3196:3200,])
    # print('#')
    # 
    # print('some random regions')
    # print(regions[1196:1200])
    # print('#')
    # print(dd.yr.wint[1,1196:1200,])
    # print('#')
    # 
    # print('some more random regions')
    # print(regions[196:200])
    # print('#')
    # print(dd.yr.wint[1,196:200,])
    # print('#')
    # 
    # print('some additional random regions')
    # print(regions[10196:10200])
    # print('#')
    # print(dd.yr.wint[1,10196:10200,])
    # print('#')
    # 
    # print('Some Canadian Regins')
    # print(regions[1:10])
    # print(year.avg[60:69])
    # print(dd.yr.wint[1,1:10,70:79])
    # print('##########')
    
    
    
  }


} else {
  marginal.tbar.tmin <- zeros.mat # marginal.tbar.temp * 0
  marginal.pbar.tmin <- zeros.mat # marginal.tbar.temp * 0
}


## dy/dTbar & dy/dPbar

marginal.tbar <- marginal.tbar.temp + marginal.tbar.prcp + marginal.tbar.tmin
marginal.pbar <- marginal.pbar.temp + marginal.pbar.prcp + marginal.pbar.tmin

if(1==0){
  # print(marginal.tbar[1000:1005,56:60])
  # print(marginal.pbar[1000:1005,56:60])
  # print(marginal.pbar.temp[1000:1005,56:60])
  # print(marginal.pbar.prcp[1000:1005,56:60])

  # print(pr.yr[1,1000:1005,56:60])
  # print(pr.yr[2,1000:1005,56:60])
  # print(pr.yr[3,1000:1005,56:60])
  # print(pr.yr[4,1000:1005,56:60])
  # print(pr.yr[5,1000:1005,56:60])
  # print(pr.yr[6,1000:1005,56:60])

  print('Tbar data:')
  print(temps.avg[1000:1005,56:60])
  # print(paste0('pr-Pbar coeff: ', get.coeff(pr_var.bin1,'seasonalpr'), '; pr-Tbar-Pbar coeff: ', get.coeff(pr_var.bin1,'seasonaltasmax*seasonalpr') ))
  print('Pbar data:')
  print(prcps.avg[1000:1005,56:60])
}


###### stop()


### These marginals need to be lagged, and then averaged over a 15-year Bartlett.
lag.and.moving.average <- function( data.mx, avg.period=15 ) {
  # A function to lag a 2-dimentional matrix of impact regions by years, then
  # compute the moving average (Bartlett kernal).
  # data.mx should be a matrix.

  tmp <- array(NA, dim=c(dim(data.mx)[1],1))
  data.mx.lag <- abind(tmp, data.mx, along=2)
  data.mx.lag <- data.mx.lag[ , 1:(dim(data.mx.lag)[2]-1) ]
  colnames(data.mx.lag) <- colnames(data.mx)

  for (r in 1:dim(data.mx.lag)[1]) {
    # Make sure there are at least some non-missing and non-inf values
    if (sum(is.finite(data.mx.lag[r,])) > 0) {
      data.mx.lag[r,] <- movavg(data.mx.lag[r,], avg.period, 'w')
    }
  }
  data.mx.lag
}

marginal.tbar.lag <- lag.and.moving.average( marginal.tbar, avg.period=15 )
marginal.pbar.lag <- lag.and.moving.average( marginal.pbar, avg.period=15 )


# Generate lagged climate vars, for calculating delta Tbar and delta Pbar.
tmp <- array(NA, dim=c(dim(temps.avg)[1],1))
temps.avg.lag <- abind(tmp, temps.avg, along=2)
temps.avg.lag <- temps.avg.lag[ , 1:(dim(temps.avg.lag)[2]-1) ]
tmp <- array(NA, dim=c(dim(prcps.avg)[1],1))
prcps.avg.lag <- abind(tmp, prcps.avg, along=2)
prcps.avg.lag <- prcps.avg.lag[ , 1:(dim(prcps.avg.lag)[2]-1) ]

# Lag and average my cost components. Now include gdd and kdd costs seperately.
marginal.tbar.avg <- lag.and.moving.average( marginal.tbar.lag, avg.period=15 )
marginal.pbar.avg <- lag.and.moving.average( marginal.pbar.lag, avg.period=15 )


## Compute costs

adpt.cost.tbar <- marginal.tbar.avg * ( temps.avg - temps.avg.lag )

adpt.cost.pbar <- marginal.pbar.avg * ( prcps.avg - prcps.avg.lag )

adpt.cost <- adpt.cost.tbar + adpt.cost.pbar


# Set NA values to zero
adpt.cost[ is.na(adpt.cost) ] <- 0

# Set 2015 and earlier to zero
baseline <- which(year.avg == 2015)
adpt.cost[ , 1:baseline ] <- 0

# Cumulative of annual marginal cost terms
cum.cost <- rowCumsums( adpt.cost )


if (is.local | output.csv) {
  # Write .csv output

  print('------------------')
  print(paste0('Writing costs for ', crop, ' under model ', model, ' / RCP ', rcp, ' / SSP', ssp, ' / IAM-',iam))
  print('------------------')

  print(paste0('!!!!!!!!!!!!! Outpath is: ', outpath, '/adaptation_costs.csv'))
  print(paste0('!!!!!!!!!!!!! working directory is: ', getwd()))

  # Assemble in a dataframe
  years.out <- rep(year.avg, each=dim(adpt.cost)[1])
  regions.out <- rep(regions, dim(adpt.cost)[2])
  df.out <- as.data.frame(cbind(regions.out, years.out, matrix(cum.cost)))
  colnames(df.out) <- c('region', 'year', 'adpt.cost.cuml')

  # Output as numeric, not factors
  df.out <- transform( df.out, adpt.cost.cuml = as.numeric(as.character(adpt.cost.cuml)) )

  write.csv( df.out, file=paste0(outpath, '/adaptation_costs.csv'), row.names=FALSE)


} else {
  # Write .netcdf output

  print('------------------')
  print(paste0('Writing costs for ', crop, ' under model ', model, ' / RCP ', rcp, ' / SSP', ssp, ' / IAM-',iam))
  print('------------------')

  my.regions <- as.character(regions)
  max.region.chars <- max(nchar(my.regions))
  years <- as.numeric(as.character(year.avg))

  dim_nchar <- ncdim_def('nchar', units='', 1:max.region.chars, create_dimvar=FALSE)
  dim_regions <- ncdim_def('region', units='', 1:length(my.regions), create_dimvar=FALSE)
  dim_time <- ncdim_def('year',  units='', years)

  var_regions <- ncvar_def(name = 'regions', units='', dim=list(dim_nchar, dim_regions), prec='char')
  var_years <- ncvar_def(name = 'years', units='', dim=list(dim_time))
  var_costs <- ncvar_def(name = 'adpt.cost.cuml', units='log_yield', dim=list(dim_regions, dim_time))

  vars <- list(var_regions, var_years, var_costs)

  # Filepath for cost output
  f.out <- paste0(outpath, '/adaptation_costs.nc4')
  costs_nc <- nc_create(f.out, vars)

  # print('cumulative costs')
  # print(cum.cost[1:5,1:5])
  # print(cum.cost[1000:1005,50:55])

  ncvar_put(costs_nc, var_regions, my.regions)
  ncvar_put(costs_nc, var_years, years)
  ncvar_put(costs_nc, var_costs, cum.cost)

  nc_close(costs_nc)

}



print("----------- DONE DONE DONE ------------")

