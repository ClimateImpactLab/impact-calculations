### Ag costs config file
# 
# Costs configurations by crop. Called by tmp_and_prcp_costs.R
# 
# NOTE: This script should be in the same directory as tmp_and_prcp_costs.R
# 
# Assumes that the <crop> variable has been set already.
#
# A. Hultgren, hultgren@berkeley.edu
# 8/11/20
###



if (crop == 'maize') {
  
  # Name of .csvv file used
  if(!is.local) {
    gammapath <- '/mnt/sacagawea_shares/gcp/social/parameters/agriculture/corn/corn-160221.csvv'
  }
  
  # Number of lines to skip when reading in the .csvv file.
  csvv.skip.lines <- 41
  
  # variables that describe gdds and kdds in the .csvv
  gdd_var <- 'gdd-8-31'
  kdd_var <- 'kdd-31'
  
  # variables that describe pr and pr^2 for the first month in each bin
  pr_var.bin1 <- 'pr-1'
  pr2_var.bin1 <- 'pr2-1'
  pr_var.bin2 <- 'pr-2'
  pr2_var.bin2 <- 'pr2-2'
  pr_var.bin3 <- 'pr-r'
  pr2_var.bin3 <- 'pr2-r'
  
  
  ### Pbar kink points. There are three separate pbar kinks: 1) GDD response, 2) KDD response, and 3) prcp quadratic response
  pbar.kink.gdd <- 200
  pbar.kink.kdd <- 100
  pbar.kink.pr <- 250
  pbar.kink.tmin <- 10
  
  # Whether or not the crop has a covariate Tbar x Pbar interaction
  has.TxP <- TRUE
  
} else if (crop == 'soy') {
  
  # Name of .csvv file used
  gammapath <-  '/mnt/sacagawea_shares/gcp/social/parameters/agriculture/soy/soy-160221.csvv' # '/mnt/sacagawea_shares/gcp/social/parameters/agriculture/soy/soy_global_t-pbar_spline_gdd-275mm_kdd-150mm_tbar_lnincbr_ir_tp_binp-tbar_pbar_spline_prcp-225mm_lnincbr_ir_tp_fe-A1TT_A0Y_clus-A1_A0Y_TINV-200316.csvv'
  
  # Number of lines to skip when reading in the .csvv file.
  csvv.skip.lines <- 35
  
  # variables that describe gdds and kdds in the .csvv
  gdd_var <- 'gdd-8-31'
  kdd_var <- 'kdd-31'
  
  # variables that describe pr and pr^2 for the first month in each bin
  pr_var.bin1 <- 'pr-1'
  pr2_var.bin1 <- 'pr2-1'
  pr_var.bin2 <- 'pr-2'
  pr2_var.bin2 <- 'pr2-2'
  pr_var.bin3 <- 'pr-3'
  pr2_var.bin3 <- 'pr2-3'
  pr_var.bin4 <- 'pr-r'
  pr2_var.bin4 <- 'pr2-r'
  
  
  ### Pbar kink points. There are three separate pbar kinks: 1) GDD response, 2) KDD response, and 3) prcp quadratic response
  pbar.kink.gdd <- 275
  pbar.kink.kdd <- 150
  pbar.kink.pr <- 225
  pbar.kink.tmin <- 10
  
  # Whether or not the crop has a covariate Tbar x Pbar interaction
  has.TxP <- TRUE
  
} else if (crop == 'rice') {
  
  # Name of .csvv file used
  gammapath <- '/mnt/sacagawea_shares/gcp/social/parameters/agriculture/rice/rice-160221.csvv'
  
  # Number of lines to skip when reading in the .csvv file.
  csvv.skip.lines <- 47
  
  # variables that describe gdds and kdds in the .csvv
  gdd_var <- 'gdd-14-30'
  kdd_var <- 'kdd-30'
  tmin_var <- 'tasmin'
  
  # variables that describe pr and pr^2 for the first month in each bin
  pr_var.bin1 <- 'pr-1'
  pr2_var.bin1 <- 'pr2-1'
  pr_var.bin2 <- 'pr-3'
  pr2_var.bin2 <- 'pr2-3'
  pr_var.bin3 <- 'pr-r'
  pr2_var.bin3 <- 'pr2-r'
  
  
  ### Pbar kink points. There are three separate pbar kinks: 1) GDD response, 2) KDD response, and 3) prcp quadratic response
  pbar.kink.gdd <- 200
  pbar.kink.kdd <- 300
  pbar.kink.pr <- 250
  pbar.kink.tmin <- 175
  
  # Whether or not the crop has a covariate Tbar x Pbar interaction
  has.TxP <- FALSE
  
} else if (crop == 'sorghum') {
  
  # Name of .csvv file used
  gammapath <- '/mnt/sacagawea_shares/gcp/social/parameters/agriculture/sorghum/sorghum-160221.csvv'
  
  # Number of lines to skip when reading in the .csvv file.
  csvv.skip.lines <- 35
  
  # variables that describe gdds and kdds in the .csvv
  gdd_var <- 'gdd-15-31'
  kdd_var <- 'kdd-31'
  
  # variables that describe pr and pr^2 for the first month in each bin
  pr_var.bin1 <- 'pr-1'
  pr2_var.bin1 <- 'pr2-1'
  pr_var.bin2 <- 'pr-2'
  pr2_var.bin2 <- 'pr2-2'
  pr_var.bin3 <- 'pr-r'
  pr2_var.bin3 <- 'pr2-r'
  
  
  ### Pbar kink points. There are three separate pbar kinks: 1) GDD response, 2) KDD response, and 3) prcp quadratic response
  pbar.kink.gdd <- 100
  pbar.kink.kdd <- 125
  pbar.kink.pr <- 100
  
  # Whether or not the crop has a covariate Tbar x Pbar interaction
  has.TxP <- FALSE
  
} else if (crop == 'cassava') {
  
  # Name of .csvv file used
  gammapath <- '/mnt/sacagawea_shares/gcp/social/parameters/agriculture/cassava/cassava-110221.csvv'
  
  # Number of lines to skip when reading in the .csvv file.
  csvv.skip.lines <- 22
  
  # variables that describe gdds and kdds in the .csvv
  gdd_var <- 'gdd-10-29'
  kdd_var <- 'kdd-29'
  
  # variables that describe pr and pr^2 for the first month in each bin
  pr_var.bin1 <- 'pr'
  pr2_var.bin1 <- 'pr2'
  
  ### Pbar kink points. There are three separate pbar kinks: 1) GDD response, 2) KDD response, and 3) prcp quadratic response
  pbar.kink.gdd <- 250
  pbar.kink.kdd <- 75
  pbar.kink.pr <- 100
  
  # Whether or not the crop has a covariate Tbar x Pbar interaction
  has.TxP <- FALSE
  
} else if (crop == 'wheat-spring') {
  
  # Name of .csvv file used
  gammapath <- '/mnt/sacagawea_shares/gcp/social/parameters/agriculture/wheat/wheat_spring-270421.csvv'
  
  # Number of lines to skip when reading in the .csvv file.
  csvv.skip.lines <- 42
  
  # variables that describe gdds and kdds in the .csvv
  gdd_var <- 'gdd-1-11'
  kdd_var <- 'kdd-11'
  tmin_var <- 'tasmin'
  
  # variables that describe pr and pr^2 for the first month in each bin
  pr_var.bin1 <- 'pr'
  pr2_var.bin1 <- 'pr2'
  pr3_var.bin1 <- 'pr3'
  pr4_var.bin1 <- 'pr4'
  
  
  ### Pbar kink points. There are three separate pbar kinks: 1) GDD response, 2) KDD response, and 3) prcp quadratic response
  pbar.kink.gdd <- 100
  pbar.kink.kdd <- 100
  pbar.kink.pr <- 125
  pbar.kink.tmin <- 125
  
  # Whether or not the crop has a covariate Tbar x Pbar interaction
  has.TxP <- TRUE

} else if (crop == 'wheat-winter') {
  
  # Name of .csvv file used
  gammapath <- '/mnt/sacagawea_shares/gcp/social/parameters/agriculture/wheat/wheat_winter-270421.csvv'
  
  # Number of lines to skip when reading in the .csvv file.
  csvv.skip.lines <- 42
  
  # variables that describe gdds and kdds in the .csvv
  # Note: the "begin", "r", and "end" terminology comes from the projection system implementation of winter wheat.
  # "begin" is fall, "end" is spring/summer, and "r" is everything else (i.e., winter).
  gdd_var.fall <- 'gdd-0-5-begin'
  kdd_var.fall <- 'kdd-5-begin'
  gdd_var.wint <- 'gdd-1-17-r'
  kdd_var.wint <- 'kdd-17-r'
  tmin_var.wint <- 'tasmin-r'
  gdd_var <- 'gdd-1-11-end' # spring/summer
  kdd_var <- 'kdd-11-end'   # spring/summer
  tmin_var <- 'tasmin-end'  # spring/summer
  
  # variables that describe pr and pr^2 for the first month in each bin
  pr_var.bin1.fall <- 'pr-begin'
  pr2_var.bin1.fall <- 'pr2-begin'
  pr3_var.bin1.fall <- 'pr3-begin'
  pr4_var.bin1.fall <- 'pr4-begin'
  pr_var.bin1.wint <- 'pr-r'
  pr2_var.bin1.wint <- 'pr2-r'
  pr3_var.bin1.wint <- 'pr3-r'
  pr4_var.bin1.wint <- 'pr4-r'
  pr_var.bin1 <- 'pr-end'   # spring/summer
  pr2_var.bin1 <- 'pr2-end' # spring/summer
  pr3_var.bin1 <- 'pr3-end' # spring/summer
  pr4_var.bin1 <- 'pr4-end' # spring/summer
  
  ### Pbar kink points. There are three separate pbar kinks: 1) GDD response, 2) KDD response, and 3) prcp quadratic response
  pbar.kink.gdd <- 100
  pbar.kink.kdd <- 100
  pbar.kink.pr <- 125
  pbar.kink.tmin <- 125
  pbar.kink.tmin.wint <- 25
  
  # Whether or not the crop has a covariate Tbar x Pbar interaction
  has.TxP <- TRUE
  
} else {
  print(paste0('Costs have not yet been configured for ', crop))
}