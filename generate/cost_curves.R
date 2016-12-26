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

allgammas <- list("global_interaction_best.nc4"=c(-.0543956572063989, -.0175858209459401, .037350265384391, .0302714957462288, .0033472344936152, .0004503090785059, -.0083214355195548, -.0018556370166573, .0022432103697581, -.0042819657236181, .0683695388864395), "global_interaction_erai.nc4"=c(-.0054022723821048, -.068831546313602, .0724052788706477, .0295227498034261, -.0079385835765961, -.010152361492013, -.0135514154278937, -.0003489024035205, .0022457454098928, -.0024712849022487, -.0352632166729257), "global_interaction_gmfd.nc4"=c(-.0592313904670902, .0013769336476968, .0677441628835927, .0280530707690405, .0179417903789245, -.0142451921364773, -.0201576093365246, -.0029591338646701, .0010307954049073, -.0021684764793275, -.0879217250776229), "global_interaction_no_popshare_best.nc4"=c(-.056395718903577, -.0192868749495498, .0205402659903872, .0327999703354906, .0029118914248846, .0007723924136599, -.0020733915791474, .0015286881411285, .0016186052150206, -.0035468165939307, .0318947490389659), "global_interaction_no_popshare_erai.nc4"=c(-.0226998470505204, -.0671191127627215, .0478838916150864, .0413001147910242, -.0062704479589512, -.0078145891965233, -.0121905502195589, .0001760603414812, .0027378727098246, -.003105997854773, -.0102973301352238), "global_interaction_no_popshare_gmfd.nc4"=c(-.067069521739972, .0005023412758493, .0515017052847762, .0180543197115543, .0225846721014261, -.0176806841733947, -.0116932283615, .0002115659351837, .0004593802062941, -.001383025670633, -.0668006789256336))

dbeta <- allgammas[[basename(filename.betas)]]

  # OPEN THE NETCDF - temps
  filename.temp <- args[2]
  nc.temps <- nc_open(filename.temp)
  temps.ann <- ncvar_get(nc.temps, 'annual') #realized temperatures
  temps.avg <- ncvar_get(nc.temps, 'averaged') #average temperatures
  regions <- ncvar_get(nc.temps, 'regions')
  year <- ncvar_get(nc.temps, 'year')
  rm(nc.temps)

  # counterfactual betas require dbeta/tbar: We need:
  ###### #1: beta(y_0, p_0, tbar_1) = beta(y_0, p_0, tbar_0) + dbeta/dtbar(tbar_1-tbar_0)
  ###### #2: beta(y_1, p_1, tbar_0) = beta(y_1, p_1, tbar_1) - dbeta/dtbar(tbar_1-tbar_0)

  costs <- array(NaN, dim=c(2, dim(regions), dim(year)-1)) # First dimenstion: LOWER BOUND IN 1, UPPER BOUND IN 2

  for (r in 1:length(regions)) {
    costs_lb <- matrix(NaN, nrow=length(year)-1,ncol=11)
    costs_ub <- matrix(NaN, nrow=length(year)-1,ncol=11)
    for (i in 1:11) {
      clip <- (betas[r, -1 ,i] == betas[r, -119, i])
      costs_lb[,i] <- temps.ann[i,r,-119] * (-dbeta[i]*(temps.avg[i,r,-1] - temps.avg[i,r,-119])) * !clip
      costs_ub[,i] <- temps.ann[i,r,-1] * (-dbeta[i]*(temps.avg[i,r,-1] - temps.avg[i,r,-119])) * !clip
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

