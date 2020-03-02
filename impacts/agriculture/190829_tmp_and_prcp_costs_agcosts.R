
################################################
# GENERATE ADAPTATION COST CURVES
# MODIFIED FOR AG
# This is an attempt to generalize the code to be able to use any functional form estimated in the response function

# T. Carleton, 3/13/2017
# A. Hultgren 5/2/2019

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

# This simplifies to: sum_k [ T_0^k * gamma_k * (Tbar_0^k - Tbar_1^k)] < COST < sum_k [ T_1^k * gamma_k * (Tbar_0^k - Tbar_1^k)], 
# where "k" indicates each term in the nonlinear response (e.g. if it's a fourth order polynomial, we have k = 1,...,4), 
# and where the Tbar values may vary by climate term (e.g for bins we interact each bin variable by the average number of days in that bin)

###########################
# Syntax: cost_curves(tavgpath, rcp, climate_model, impactspath), Where:
# tavgpath = filepath for long run average climate data by impact region year
# rcp = which RCP? enter as a string --  'rcp85' or 'rcp45'
# climate_model = which climate model? enter as a string -- e.g. 'MIROC-ESM'
# impactspath = filepath for the projected impacts for this model
###########################

###############################################

rm(list=ls())

require(dplyr)
library(pracma)
library(ncdf4)
library(dplyr)
library(DataCombine)
library(zoo)
library(abind)
#library(rPython)
#source("generate/stochpower.R")

#####################
is.local <- T
if(is.local) {
  # Tamma's paths
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
if(is.local) {
  # Andy's paths
  tavgpath <- 'C:/Users/Andy Hultgren/Documents/ARE/GSR/GCP/Ag/Projections/single-corn-190326/corn_prsplitmodel-allcalcs-corn_global_t-tbar_pbar_lnincbr_ir_tp_binp-tbar_pbar_lnincbr_ir_tp-190326.csv'
  #tannpath <- 'C:/Users/Andy Hultgren/Documents/ARE/GSR/GCP/Ag/Projections/adaptation_costs_test/climate-data/edd_monthly'
  outpath <- 'C:/Users/Andy Hultgren/Documents/ARE/GSR/GCP/Ag/Projections/single-corn-190326/output'
  #impactspath <- 'C:/Users/Andy Hultgren/Documents/ARE/GSR/GCP/Ag/Projections/adaptation_costs_test/impacts-mealy/corn_global_t-tbar_pbar_lnincbr_ir_tp_binp-tbar_pbar_lnincbr_ir_tp_time_invariant_fe-A1TT_A0Y_clus-A1_A0Y-190326.nc4'
  gammapath <- 'C:/Users/Andy Hultgren/Documents/ARE/GSR/GCP/Ag/Projections/single-corn-190326/csvv/corn_global_t-tbar_pbar_lnincbr_ir_tp_binp-tbar_pbar_lnincbr_ir_tp_time_invariant_fe-A1TT_A0Y_clus-A1_A0Y-190326.csvv'
  #gammarange <- 25:36 #oldest! 
  #minpath <- "~/Dropbox/Tamma-Shackleton/GCP/adaptation_costs/data/poly_dailyclip/global_interaction_Tmean-POLY-4-AgeSpec-oldest-polymins.csv"
  #model <- 'poly'
  #powers <- 4
  #avgmethod <- 'bartlett'
}
#####################

###############################################
# Set up
###############################################

if (1==0) {
  # Mortality code
  
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
}


##############################################################################################
# LOAD realized climate variable from single folder
##############################################################################################

if(is.local) {
  # Andy's setup for ag costs
  df.tavg <- read.csv(tavgpath, skip=42)
  # temps.avg <- df.tavg$seasonaltasmax #average temperatures
  # regions <- df.tavg$region
  # year.avg <- df.tavg$year
  
} else {
  # OPEN THE NETCDF - average temps
  nc.tavg <- nc_open(tavgpath)
  temps.avg <- ncvar_get(nc.tavg, 'averaged') #average temperatures
  regions <- ncvar_get(nc.tavg, 'regions')
  year.avg <- ncvar_get(nc.tavg, 'year')
  
}

##############################################################################################
# LOAD ADAPTIVE INVESTMENTS TERM -- FROM JAMES' OUTPUT
##############################################################################################

if (1==0) {
  # Mortality needs this due to its various forms of clipping. 
  # For ag, I don't use this term, so skip it.
  nc.imp <- nc_open(impactspath)
  impacts.climtaseff <- ncvar_get(nc.imp, 'climtas_effect') # Sum of adaptive investments at daily level
  
  #check whether timesteps in climate file = timesteps in impacts file
  if (length(year.avg) != length(ncvar_get(nc.imp, 'year'))) { 
    impacts.climtaseff <- impacts.climtaseff[, 1:length(year.avg)] 
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
  
}

##############################################################################################
# Generate a moving average of the adaptive investments term
# For ag, I think the moving average should just be over Tbar and Pbar.
##############################################################################################

# For ag, Tbar and Pbar are in the allcalcs file which is a .csv (so, read as a dataframe).
# So, let's just use dplyr for this.

# Bartlett kernal over 30 years, and the one year lags
df.tavg <- df.tavg %>%
  group_by(region) %>%
  mutate( seasonaltasmax.lag = lag( seasonaltasmax, order_by=region ) ) %>%
  mutate( seasonalpr.lag = lag( seasonalpr, order_by=region ) ) %>%
  mutate( avgtbar = movavg(seasonaltasmax, 30, 'w')  ) %>%
  mutate( avgpbar = movavg(seasonalpr, 30, 'w')  ) %>%
  mutate( avgtbar.lag = lag(avgtbar, order_by=region)) %>%
  mutate( avgpbar.lag = lag(avgpbar, order_by=region)) %>%
  mutate( avggdd = movavg(gdd.8.29, 30, 'w')  ) %>%
  mutate( avgkdd = movavg(kdd.29, 30, 'w')  ) %>%
  mutate( avggdd.lag = lag(avggdd, order_by=region)) %>%
  mutate( avgkdd.lag = lag(avgkdd, order_by=region)) %>%
  # The following lines are included because I am not sure how the actual monthly
  # precip data (.nc files of projected climate data) lines up with the precip 
  # coefficient values for each growing season month.
  mutate( avgpr = movavg(pr/12, 30, 'w') ) %>%
  mutate( avgpr2 = movavg(pr.poly.2/12, 30, 'w') ) %>%
  mutate( avgpr.lag = lag(avgpr, order_by=region)) %>%
  mutate( avgpr2.lag = lag(avgpr2, order_by=region)) %>%
  # 2010 average values are needed for the cost lower bound.
  mutate ( avggdd.2010 = avggdd[which(year==2010)] ) %>%
  mutate ( avgkdd.2010 = avgkdd[which(year==2010)] ) %>%
  mutate ( avgpr.2010 = avgpr[which(year==2010)] ) %>%
  mutate ( avgpr2.2010 = avgpr2[which(year==2010)] ) %>%
  mutate( seasonaltasmax.2010 = seasonaltasmax[which(year==2010)] ) %>%
  mutate( seasonalpr.2010 = seasonalpr[which(year==2010)] ) %>%
  ungroup()


# View(df.tavg[ df.tavg$region=='BRA.13.1818.3664', ])

# Mortality code
if (1==0) {
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
  
}


print("MOVING AVERAGE OF ADAPTIVE INVESTMENTS CALCULATED")

###############################################
# For each region-year, calculate lower and upper bounds
###############################################

# For ag, calculate the costs by multiplying out the actual necessary coefficients, and using realized gdd, kdd, and prcp.
# !!!!!!!!! CHECK WITH JAMES TO MAKE SURE THIS IS APPROPRIATE !!!!!!!!!!!!!!!!!!!


#clim.vars <- c('gdd-8-29', 'kdd-29', 'pr-1','pr2-1','pr-2','pr2-2', 'pr-3','pr2-3','pr-4','pr2-4',
#               'pr-5','pr2-5','pr-6','pr2-6','pr-7','pr2-7','pr-8', 'pr2-8', 'pr-9', 'pr2-9', 'pr-r', 'pr2-r')
#cov.vars <- c('1', 'seasonaltasmax', 'seasonalpr', 'loggdppc', 'ir-share', 'seasonaltasmax*seasonalpr')


# Read in the regression coefficients from the .csvv file and grab three rows:
# The row of predictor names, the row of covariate names, and the row of coefficient values.
coeffs <- read.csv(gammapath, skip=38, header=FALSE, stringsAsFactors=FALSE)
coeffs <- coeffs [c(1,3,5),]
# Trim whitespace from predictor and covariate names
coeffs[1,] <- trimws(coeffs[1,])
coeffs[2,] <- trimws(coeffs[2,])


get.coeff <- function( clim, cov, csvv.df=coeffs ) {
  # Given a .csvv file read in above from gammapath, find the coefficient corresponding to the 
  # interaction between <clim> (the weather parameter) and <cov> (the covariate). For main effects
  # of the <clim> parameters, pass a string of '1' as the argument for <cov>.
  
  return(as.numeric( csvv.df[3, (csvv.df[1,] %in% clim) & (csvv.df[2,] %in% cov)] ))
}




# In every year-ir that is clipped, force the costs to be zero. 
# Check for clipping in GDD (clip if GDD coeff < 0) and in KDD (clip if KDD coeff > 0).
# This filter takes a value of 1 when costs should be clipped. Apply it when calculating costs.
gdd.clip.filter <- ( 0 < 
                       get.coeff('gdd-8-29','1') + 
                       get.coeff('gdd-8-29','seasonaltasmax')*df.tavg$seasonaltasmax +
                       get.coeff('gdd-8-29','seasonalpr')*df.tavg$seasonalpr +
                       get.coeff('gdd-8-29','seasonaltasmax*seasonalpr')*df.tavg$seasonaltasmax.seasonalpr +
                       get.coeff('gdd-8-29','loggdppc')*df.tavg$loggdppc +
                       get.coeff('gdd-8-29','ir-share')*df.tavg$ir.share 
                     )

kdd.clip.filter <- ( 0 > 
                       get.coeff('kdd-29','1') + 
                       get.coeff('kdd-29','seasonaltasmax')*df.tavg$seasonaltasmax +
                       get.coeff('kdd-29','seasonalpr')*df.tavg$seasonalpr +
                       get.coeff('kdd-29','seasonaltasmax*seasonalpr')*df.tavg$seasonaltasmax.seasonalpr +
                       get.coeff('kdd-29','loggdppc')*df.tavg$loggdppc +
                       get.coeff('kdd-29','ir-share')*df.tavg$ir.share 
                     )

# Set NA values to zero
gdd.clip.filter[is.na(gdd.clip.filter)] <- 0
kdd.clip.filter[is.na(kdd.clip.filter)] <- 0


# Temperature response adaptation costs to changing Tbar
# !!!! For the lower bound, should I be using df.tavg$seasonalpr.2010 ?? I think so, but check the math and confirm...
df.tavg$adpt.cost.tmp.tbar.lower <- ( df.tavg$avggdd.2010 * gdd.clip.filter *
                                        ( get.coeff('gdd-8-29','seasonaltasmax') + get.coeff('gdd-8-29','seasonaltasmax*seasonalpr')*df.tavg$seasonalpr.2010 ) +
                                      df.tavg$avgkdd.2010 * kdd.clip.filter *
                                        ( get.coeff('kdd-29','seasonaltasmax') + get.coeff('kdd-29','seasonaltasmax*seasonalpr')*df.tavg$seasonalpr.2010 )
                                    ) * ( df.tavg$seasonaltasmax.lag - df.tavg$seasonaltasmax )


df.tavg$adpt.cost.tmp.tbar.upper <- ( df.tavg$avggdd.lag * gdd.clip.filter *
                                        ( get.coeff('gdd-8-29','seasonaltasmax') + get.coeff('gdd-8-29','seasonaltasmax*seasonalpr')*df.tavg$seasonalpr ) +
                                      df.tavg$avgkdd.lag * kdd.clip.filter *
                                        ( get.coeff('kdd-29','seasonaltasmax') + get.coeff('kdd-29','seasonaltasmax*seasonalpr')*df.tavg$seasonalpr )
                                    ) * ( df.tavg$seasonaltasmax.lag - df.tavg$seasonaltasmax )



# Temperature response adaptation costs to changing Pbar
df.tavg$adpt.cost.tmp.pbar.lower <- ( df.tavg$avggdd.2010 * gdd.clip.filter *
                                        ( get.coeff('gdd-8-29','seasonalpr') + get.coeff('gdd-8-29','seasonaltasmax*seasonalpr')*df.tavg$seasonaltasmax.2010 ) +
                                        df.tavg$avgkdd.2010 * kdd.clip.filter *
                                        ( get.coeff('kdd-29','seasonalpr') + get.coeff('kdd-29','seasonaltasmax*seasonalpr')*df.tavg$seasonaltasmax.2010 )
                                    ) * ( df.tavg$seasonalpr.lag - df.tavg$seasonalpr )


df.tavg$adpt.cost.tmp.pbar.upper <- ( df.tavg$avggdd.lag * gdd.clip.filter *
                                        ( get.coeff('gdd-8-29','seasonalpr') + get.coeff('gdd-8-29','seasonaltasmax*seasonalpr')*df.tavg$seasonaltasmax ) +
                                        df.tavg$avgkdd.lag * kdd.clip.filter *
                                        ( get.coeff('kdd-29','seasonalpr') + get.coeff('kdd-29','seasonaltasmax*seasonalpr')*df.tavg$seasonaltasmax )
                                    ) * ( df.tavg$seasonalpr.lag - df.tavg$seasonalpr )




# Precipitation response adaptation costs to changing Tbar, the "remaining" month group r
df.tavg$adpt.cost.prcp.tbar.lower <- ( df.tavg$avgpr.2010 * 
                                         ( get.coeff('pr-r','seasonaltasmax') + get.coeff('pr-r','seasonaltasmax*seasonalpr')*df.tavg$seasonalpr.2010 ) +
                                       df.tavg$avgpr2.2010 *
                                         ( get.coeff('pr2-r','seasonaltasmax') + get.coeff('pr2-r','seasonaltasmax*seasonalpr')*df.tavg$seasonalpr.2010 )
                                     ) * ( df.tavg$seasonaltasmax.lag - df.tavg$seasonaltasmax )


df.tavg$adpt.cost.prcp.tbar.upper <- ( df.tavg$avgpr.lag * 
                                         ( get.coeff('pr-r','seasonaltasmax') + get.coeff('pr-r','seasonaltasmax*seasonalpr')*df.tavg$seasonalpr ) +
                                       df.tavg$avgpr2.lag *
                                         ( get.coeff('pr2-r','seasonaltasmax') + get.coeff('pr2-r','seasonaltasmax*seasonalpr')*df.tavg$seasonalpr )
                                     ) * ( df.tavg$seasonaltasmax.lag - df.tavg$seasonaltasmax )


# Precipitation response adaptation costs to changing Pbar
df.tavg$adpt.cost.prcp.pbar.lower <- ( df.tavg$avgpr.2010 * 
                                         ( get.coeff('pr-r','seasonalpr') + get.coeff('pr-r','seasonaltasmax*seasonalpr')*df.tavg$seasonaltasmax.2010 ) +
                                       df.tavg$avgpr2.2010 *
                                         ( get.coeff('pr2-r','seasonalpr') + get.coeff('pr2-r','seasonaltasmax*seasonalpr')*df.tavg$seasonaltasmax.2010 )
                                     ) * ( df.tavg$seasonaltasmax.lag - df.tavg$seasonaltasmax )


df.tavg$adpt.cost.prcp.pbar.upper <- ( df.tavg$avgpr.lag * 
                                         ( get.coeff('pr-r','seasonalpr') + get.coeff('pr-r','seasonaltasmax*seasonalpr')*df.tavg$seasonaltasmax ) +
                                       df.tavg$avgpr2.lag *
                                         ( get.coeff('pr2-r','seasonalpr') + get.coeff('pr2-r','seasonaltasmax*seasonalpr')*df.tavg$seasonaltasmax )
                                     ) * ( df.tavg$seasonaltasmax.lag - df.tavg$seasonaltasmax )




# Repeat for pr coeffs 1-9
for (mo in 1:9) {
  pr.str <- paste0('pr-',mo)
  pr2.str <- paste0('pr2-',mo)
  
  # Precipitation response adaptation costs to changing Tbar
  df.tavg$adpt.cost.prcp.tbar.lower <- ( df.tavg$avgpr.2010 * 
                                           ( get.coeff(pr.str,'seasonaltasmax') + get.coeff(pr.str,'seasonaltasmax*seasonalpr')*df.tavg$seasonalpr.2010 ) +
                                           df.tavg$avgpr2.2010 *
                                           ( get.coeff(pr2.str,'seasonaltasmax') + get.coeff(pr2.str,'seasonaltasmax*seasonalpr')*df.tavg$seasonalpr.2010 )
                                       ) * ( df.tavg$seasonaltasmax.lag - df.tavg$seasonaltasmax ) + df.tavg$adpt.cost.prcp.tbar.lower
  
  
  df.tavg$adpt.cost.prcp.tbar.upper <- ( df.tavg$avgpr.lag * 
                                           ( get.coeff(pr.str,'seasonaltasmax') + get.coeff(pr.str,'seasonaltasmax*seasonalpr')*df.tavg$seasonalpr ) +
                                           df.tavg$avgpr2.lag *
                                           ( get.coeff(pr2.str,'seasonaltasmax') + get.coeff(pr2.str,'seasonaltasmax*seasonalpr')*df.tavg$seasonalpr )
                                       ) * ( df.tavg$seasonaltasmax.lag - df.tavg$seasonaltasmax ) + df.tavg$adpt.cost.prcp.tbar.upper
  
  
  # Precipitation response adaptation costs to changing Pbar
  df.tavg$adpt.cost.prcp.pbar.lower <- ( df.tavg$avgpr.2010 * 
                                           ( get.coeff(pr.str,'seasonalpr') + get.coeff(pr.str,'seasonaltasmax*seasonalpr')*df.tavg$seasonaltasmax.2010 ) +
                                           df.tavg$avgpr2.2010 *
                                           ( get.coeff(pr2.str,'seasonalpr') + get.coeff(pr2.str,'seasonaltasmax*seasonalpr')*df.tavg$seasonaltasmax.2010 )
                                        ) * ( df.tavg$seasonaltasmax.lag - df.tavg$seasonaltasmax ) + df.tavg$adpt.cost.prcp.pbar.lower
  
  
  df.tavg$adpt.cost.prcp.pbar.upper <- ( df.tavg$avgpr.lag * 
                                           ( get.coeff(pr.str,'seasonalpr') + get.coeff(pr.str,'seasonaltasmax*seasonalpr')*df.tavg$seasonaltasmax ) +
                                           df.tavg$avgpr2.lag *
                                           ( get.coeff(pr2.str,'seasonalpr') + get.coeff(pr2.str,'seasonaltasmax*seasonalpr')*df.tavg$seasonaltasmax )
                                       ) * ( df.tavg$seasonaltasmax.lag - df.tavg$seasonaltasmax ) + df.tavg$adpt.cost.prcp.pbar.upper
  
}

### Aggregate adaptation costs by response (temp vs. prcp) and by climate (Tbar vs. Pbar) to see where adaptation costs are coming from.
### Then aggregate to total adaptation costs.

# costs by precip
df.tavg$adpt.cost.prcp.lower <- df.tavg$adpt.cost.prcp.pbar.lower + df.tavg$adpt.cost.prcp.tbar.lower
df.tavg$adpt.cost.prcp.upper <- df.tavg$adpt.cost.prcp.pbar.upper + df.tavg$adpt.cost.prcp.tbar.upper

# costs by temp
df.tavg$adpt.cost.tmp.lower <- df.tavg$adpt.cost.tmp.pbar.lower + df.tavg$adpt.cost.tmp.tbar.lower
df.tavg$adpt.cost.tmp.upper <- df.tavg$adpt.cost.tmp.pbar.upper + df.tavg$adpt.cost.tmp.tbar.upper

# costs by tbar
df.tavg$adpt.cost.tbar.lower <- df.tavg$adpt.cost.tmp.tbar.lower + df.tavg$adpt.cost.prcp.tbar.lower
df.tavg$adpt.cost.tbar.upper <- df.tavg$adpt.cost.tmp.tbar.upper + df.tavg$adpt.cost.prcp.tbar.upper

# costs by pbar
df.tavg$adpt.cost.pbar.lower <- df.tavg$adpt.cost.tmp.pbar.lower + df.tavg$adpt.cost.prcp.pbar.lower
df.tavg$adpt.cost.pbar.upper <- df.tavg$adpt.cost.tmp.pbar.upper + df.tavg$adpt.cost.prcp.pbar.upper

# total costs
df.tavg$adpt.cost.lower <- df.tavg$adpt.cost.tbar.lower + df.tavg$adpt.cost.pbar.lower
df.tavg$adpt.cost.upper <- df.tavg$adpt.cost.tbar.upper + df.tavg$adpt.cost.pbar.upper

# Set NA values to zero
df.tavg$adpt.cost.lower[ is.na(df.tavg$adpt.cost.lower) ] <- 0
df.tavg$adpt.cost.upper[ is.na(df.tavg$adpt.cost.upper) ] <- 0
df.tavg$adpt.cost.prcp.lower[ is.na(df.tavg$adpt.cost.prcp.lower) ] <- 0
df.tavg$adpt.cost.prcp.upper[ is.na(df.tavg$adpt.cost.prcp.upper) ] <- 0
df.tavg$adpt.cost.tmp.lower[ is.na(df.tavg$adpt.cost.tmp.lower) ] <- 0
df.tavg$adpt.cost.tmp.upper[ is.na(df.tavg$adpt.cost.tmp.upper) ] <- 0


# Focus on cumulative costs, per Tamma.
df.tavg <- df.tavg %>%
  group_by( region ) %>%
  arrange( year, .by_group=TRUE ) %>%
  mutate( adpt.cost.lower.cuml = cumsum(adpt.cost.lower) ) %>%
  mutate( adpt.cost.upper.cuml = cumsum(adpt.cost.upper) ) %>%
  mutate( adpt.cost.prcp.lower.cuml = cumsum(adpt.cost.prcp.lower) ) %>%
  mutate( adpt.cost.prcp.upper.cuml = cumsum(adpt.cost.prcp.upper) ) %>%
  mutate( adpt.cost.tmp.lower.cuml = cumsum(adpt.cost.tmp.lower) ) %>%
  mutate( adpt.cost.tmp.upper.cuml = cumsum(adpt.cost.tmp.upper) ) %>%
  ungroup()

columns.to.keep <- c( 'region', 'year', 'adpt.cost.tmp.lower.cuml', 'adpt.cost.tmp.upper.cuml', 
                      'adpt.cost.prcp.lower.cuml', 'adpt.cost.prcp.upper.cuml', 'adpt.cost.upper.cuml', 'adpt.cost.lower.cuml' )

df.tavg <- df.tavg[ , columns.to.keep ]

# Write to .csv
write.csv( df.tavg, file=paste0(outpath, '/corn_single_190326_costs.csv'), row.names=FALSE)

# View(df.tavg[1:50,])
# View(df.tavg[ df.tavg$region=='AUS.5.392',])





if (1 == 0) {
  # Mortality
  
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
  
}

print("----------- DONE DONE DONE ------------")
