
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

#####################
is.local <- T
if(is.local) {
  # Andy's paths
  tavgpath <- 'C:/Users/Andy Hultgren/Documents/ARE/GSR/GCP/Ag/Projections/adaptation_costs_test/impacts-mealy/single-corn-tbar-spline-nogddclip-costs-191218/corn_prsplitmodel-allcalcs-corn_191220.csv'
  outpath <- 'C:/Users/Andy Hultgren/Documents/ARE/GSR/GCP/Ag/Projections/adaptation_costs_test/impacts-mealy/single-corn-tbar-spline-nogddclip-costs-191218/output'
  gammapath <- 'C:/Users/Andy Hultgren/Documents/ARE/GSR/GCP/Ag/Projections/adaptation_costs_test/impacts-mealy/single-corn-tbar-spline-nogddclip-costs-191218/csvv/corn_global_t-tbar_pbar_lnincbr_ir_tp_binp-tbar_pbar_lnincbr_ir_tp_fe-A1TT_A0Y_clus-A1_A0Y_TINV-191220.csvv'
  
  tavgpath <- 'C:/Users/Andy Hultgren/Documents/ARE/GSR/GCP/Ag/Projections/adaptation_costs_test/impacts-mealy/single-corn-kdd-cutoff31-precip-bins-costs/corn-allcalcs-191220.csv'
  outpath <- 'C:/Users/Andy Hultgren/Documents/ARE/GSR/GCP/Ag/Projections/adaptation_costs_test/impacts-mealy/single-corn-kdd-cutoff31-precip-bins-costs/output'
  gammapath <- 'C:/Users/Andy Hultgren/Documents/ARE/GSR/GCP/Ag/Projections/adaptation_costs_test/impacts-mealy/single-corn-kdd-cutoff31-precip-bins-costs/csvv/corn_global_t-tbar_pbar_lnincbr_ir_tp_binp-tbar_pbar_lnincbr_ir_tp_fe-A1TT_A0Y_clus-A1_A0Y_TINV-191220.csvv'
  
  # tavgpath <- 'C:/Users/Andy Hultgren/Documents/ARE/GSR/GCP/Ag/Projections/adaptation_costs_test/impacts-mealy/corn_global_t-tbar_pbar_lnincbr_ir_tp_binp-tbar_pbar_lnincbr_ir_tp_fe-A1TT_A0Y_clus-A1_A0Y_TINV-191220.nc4'
  # outpath <- 'C:/Users/Andy Hultgren/Documents/ARE/GSR/GCP/Ag/Projections/adaptation_costs_test/impacts-mealy/output'
  # gammapath <- 'C:/Users/Andy Hultgren/Documents/ARE/GSR/GCP/Ag/Projections/single-corn-190326/csvv/corn_global_t-tbar_pbar_lnincbr_ir_tp_binp-tbar_pbar_lnincbr_ir_tp_time_invariant_fe-A1TT_A0Y_clus-A1_A0Y-190326.csvv'
  
  # Set this to TRUE if outputting marginal effects of climate terms for diagnostics / development.  Otherwise set to FALSE.
  compute_marginals <- TRUE
  
}
#####################



##############################################################################################
# LOAD realized climate variable from single folder
##############################################################################################

if(is.local) {
  # Andy's setup for ag costs
  df.tavg <- read.csv(tavgpath, skip=108) # skip=42, skip=108
  
} else {
  # OPEN THE NETCDF - average temps
  nc.tavg <- nc_open(tavgpath)
  temps.avg <- ncvar_get(nc.tavg, 'averaged') #average temperatures
  regions <- ncvar_get(nc.tavg, 'regions')
  year.avg <- ncvar_get(nc.tavg, 'year')
  
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
  mutate( avggdd = movavg(gdd.8.31, 30, 'w')  ) %>%
  mutate( avgkdd = movavg(kdd.31, 30, 'w')  ) %>%
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


###############################################
# For each region-year, calculate lower and upper bounds
###############################################



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
gdd_var <- 'gdd-8-31'
kdd_var <- 'kdd-31'
no_gdd_clip <- TRUE

gdd.clip.filter <- ( 0 < 
                       get.coeff(gdd_var,'1') + 
                       get.coeff(gdd_var,'seasonaltasmax')*df.tavg$seasonaltasmax +
                       get.coeff(gdd_var,'seasonalpr')*df.tavg$seasonalpr +
                       get.coeff(gdd_var,'seasonaltasmax*seasonalpr')*df.tavg$seasonaltasmax.seasonalpr +
                       get.coeff(gdd_var,'loggdppc')*df.tavg$loggdppc +
                       get.coeff(gdd_var,'ir-share')*df.tavg$ir.share 
                     )


kdd.clip.filter <- ( 0 > 
                       get.coeff(kdd_var,'1') + 
                       get.coeff(kdd_var,'seasonaltasmax')*df.tavg$seasonaltasmax +
                       get.coeff(kdd_var,'seasonalpr')*df.tavg$seasonalpr +
                       get.coeff(kdd_var,'seasonaltasmax*seasonalpr')*df.tavg$seasonaltasmax.seasonalpr +
                       get.coeff(kdd_var,'loggdppc')*df.tavg$loggdppc +
                       get.coeff(kdd_var,'ir-share')*df.tavg$ir.share 
                     )

if(no_gdd_clip) {
  gdd.clip.filter <- as.logical( gdd.clip.filter*0 + 1 )
  # Set NA values
  gdd.clip.filter[is.na(gdd.clip.filter)] <- 1
  kdd.clip.filter[is.na(kdd.clip.filter)] <- 0

} else {
  # Set NA values to zero
  gdd.clip.filter[is.na(gdd.clip.filter)] <- 0
  kdd.clip.filter[is.na(kdd.clip.filter)] <- 0
}




if (compute_marginals) {
  
  # For diagnostic purposes, compute the upper bound marginal effects of climate
  # Naming convention: marginal.[covariate].[temp or prcp]   
  # E.g., marginal.tbar.temp is the marginal effect of Tbar through the temperature terms (gdd and kdd)
  
  df.tavg$marginal.tbar.temp <- ( df.tavg$avggdd.lag * gdd.clip.filter *
                                    ( get.coeff(gdd_var,'seasonaltasmax') + get.coeff(gdd_var,'seasonaltasmax*seasonalpr')*df.tavg$seasonalpr ) +
                                  df.tavg$avgkdd.lag * kdd.clip.filter *
                                    ( get.coeff(kdd_var,'seasonaltasmax') + get.coeff(kdd_var,'seasonaltasmax*seasonalpr')*df.tavg$seasonalpr )
                                )
  
  # Note: this term incorrect due to approximation used for avgpr
  df.tavg$marginal.tbar.prcp <- ( df.tavg$avgpr.lag * 
                                    ( get.coeff('pr-r','seasonaltasmax') + get.coeff('pr-r','seasonaltasmax*seasonalpr')*df.tavg$seasonalpr ) +
                                  df.tavg$avgpr2.lag *
                                    ( get.coeff('pr2-r','seasonaltasmax') + get.coeff('pr2-r','seasonaltasmax*seasonalpr')*df.tavg$seasonalpr )
                                )
  
  
  df.tavg$marginal.pbar.temp <- ( df.tavg$avggdd.lag * gdd.clip.filter *
                                    ( get.coeff(gdd_var,'seasonalpr') + get.coeff(gdd_var,'seasonaltasmax*seasonalpr')*df.tavg$seasonaltasmax ) +
                                  df.tavg$avgkdd.lag * kdd.clip.filter *
                                    ( get.coeff(kdd_var,'seasonalpr') + get.coeff(kdd_var,'seasonaltasmax*seasonalpr')*df.tavg$seasonaltasmax )
                                )
  
  # Note: this term incorrect due to approximation used for avgpr
  df.tavg$marginal.pbar.prcp <- ( df.tavg$avgpr.lag * 
                                    ( get.coeff('pr-r','seasonalpr') + get.coeff('pr-r','seasonaltasmax*seasonalpr')*df.tavg$seasonaltasmax ) +
                                  df.tavg$avgpr2.lag *
                                    ( get.coeff('pr2-r','seasonalpr') + get.coeff('pr2-r','seasonaltasmax*seasonalpr')*df.tavg$seasonaltasmax )
                                )
  
}



# Temperature response adaptation costs to changing Tbar
# !!!! For the lower bound, should I be using df.tavg$seasonalpr.2010 ?? I think so, but check the math and confirm...
df.tavg$adpt.cost.tmp.tbar.lower <- ( df.tavg$avggdd.2010 * gdd.clip.filter *
                                        ( get.coeff(gdd_var,'seasonaltasmax') + get.coeff(gdd_var,'seasonaltasmax*seasonalpr')*df.tavg$seasonalpr.2010 ) +
                                      df.tavg$avgkdd.2010 * kdd.clip.filter *
                                        ( get.coeff(kdd_var,'seasonaltasmax') + get.coeff(kdd_var,'seasonaltasmax*seasonalpr')*df.tavg$seasonalpr.2010 )
                                    ) * ( df.tavg$seasonaltasmax.lag - df.tavg$seasonaltasmax )


df.tavg$adpt.cost.tmp.tbar.upper <- ( df.tavg$avggdd.lag * gdd.clip.filter *
                                        ( get.coeff(gdd_var,'seasonaltasmax') + get.coeff(gdd_var,'seasonaltasmax*seasonalpr')*df.tavg$seasonalpr ) +
                                      df.tavg$avgkdd.lag * kdd.clip.filter *
                                        ( get.coeff(kdd_var,'seasonaltasmax') + get.coeff(kdd_var,'seasonaltasmax*seasonalpr')*df.tavg$seasonalpr )
                                    ) * ( df.tavg$seasonaltasmax.lag - df.tavg$seasonaltasmax )



# Temperature response adaptation costs to changing Pbar
df.tavg$adpt.cost.tmp.pbar.lower <- ( df.tavg$avggdd.2010 * gdd.clip.filter *
                                        ( get.coeff(gdd_var,'seasonalpr') + get.coeff(gdd_var,'seasonaltasmax*seasonalpr')*df.tavg$seasonaltasmax.2010 ) +
                                        df.tavg$avgkdd.2010 * kdd.clip.filter *
                                        ( get.coeff(kdd_var,'seasonalpr') + get.coeff(kdd_var,'seasonaltasmax*seasonalpr')*df.tavg$seasonaltasmax.2010 )
                                    ) * ( df.tavg$seasonalpr.lag - df.tavg$seasonalpr )


df.tavg$adpt.cost.tmp.pbar.upper <- ( df.tavg$avggdd.lag * gdd.clip.filter *
                                        ( get.coeff(gdd_var,'seasonalpr') + get.coeff(gdd_var,'seasonaltasmax*seasonalpr')*df.tavg$seasonaltasmax ) +
                                        df.tavg$avgkdd.lag * kdd.clip.filter *
                                        ( get.coeff(kdd_var,'seasonalpr') + get.coeff(kdd_var,'seasonaltasmax*seasonalpr')*df.tavg$seasonaltasmax )
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


if (compute_marginals) {
  
  # James also needs seasonaltasmax and seasonalpr for diagnostics, as well as the marginal effects of climate
  columns.to.keep <- c( 'region', 'year', 'seasonaltasmax', 'seasonalpr', 'adpt.cost.tmp.lower.cuml', 'adpt.cost.tmp.upper.cuml', 
                        'adpt.cost.prcp.lower.cuml', 'adpt.cost.prcp.upper.cuml', 'adpt.cost.upper.cuml', 'adpt.cost.lower.cuml',
                        'marginal.tbar.temp', 'marginal.tbar.prcp', 'marginal.pbar.temp', 'marginal.pbar.prcp')
}


df.tavg.final <- df.tavg[ , columns.to.keep ]

# Write to .csv
write.csv( df.tavg.final, file=paste0(outpath, '/corn_single_200121_costs.csv'), row.names=FALSE)

# View(df.tavg[1:50,])
# View(df.tavg[ df.tavg$region=='AUS.5.392',])


if(1==0) {
  
  df.tavg.final$marginal.tbar <- df.tavg.final$marginal.tbar.temp + df.tavg.final$marginal.tbar.prcp
  df.tavg.final$marginal.pbar <- df.tavg.final$marginal.pbar.temp + df.tavg.final$marginal.pbar.prcp
  
  my_ir <- 'USA.11.422'
  filt <- df.tavg.final$region %in% my_ir
  View(df.tavg.final[filt, c('region', 'year', 'marginal.tbar', 'marginal.pbar')])
  
  nc.impacts <- nc_open('C:/Users/Andy Hultgren/Documents/ARE/GSR/GCP/Ag/Projections/adaptation_costs_test/impacts-mealy/single-corn-kdd-cutoff31-precip-bins-costs/corn_global_t-tbar_pbar_lnincbr_ir_tp_binp-tbar_pbar_lnincbr_ir_tp_fe-A1TT_A0Y_clus-A1_A0Y_TINV-191220.nc4')
  print(nc.impacts)
  
  regions <- ncvar_get(nc.impacts, 'regions')
  years <- ncvar_get(nc.impacts, 'year')
  years
  ddseasonalpr <- ncvar_get(nc.impacts, 'ddseasonalpr')
  ddseasonaltasmax <- ncvar_get(nc.impacts, 'ddseasonaltasmax')  
  
  region_idx <- which(regions==my_ir)
  test.out <- cbind(years, ddseasonaltasmax[region_idx,], ddseasonalpr[region_idx,])
  colnames(test.out) <- c('year', 'ddseasonaltasmax', 'ddseasonalpr')
  View(test.out)
  
}



print("----------- DONE DONE DONE ------------")
