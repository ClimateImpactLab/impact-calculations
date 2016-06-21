setwd("~/Repos/impact-calculations/interpolate")

source("bayeser.R")

# Specification of 1st Stage model
K <- 11
spec <- "original"

# Specification of 2nd Stage model
L <- 4
include.2stgfe <- FALSE

## VCV files
basedir <- "/shares/gcp/data/adaptation/vcvs"
#basedir <- "~/Dropbox/ChicagoRAs_Reanalysis/interpolation/output/final/VCV_files"
dirs <- c("BRAZIL", "CHINA", "INDIA", "MEXICO")

## Beta files-- may be longer than VCV list
betadir <- "/shares/gcp/data/adaptation/inputs-apr-7"
#betadir <- "~/Dropbox/ChicagoRAs_Reanalysis/interpolation/output/income_matched"
fe.units <- c("BRA", "CHN", "IND", "MEX", "FRA", "USA")
adms <- paste0(fe.units, "_adm1.csv")
#adms <- paste0(fe.units, "_adm1_", spec, ".csv")
#adms <- c("BRA_adm1_trends.csv", "CHN_adm1_trends.csv", "IND_adm1_trends.csv", "MEX_adm1_trends.csv", "FRA_adm1_trends.csv", "USA_adm1_trends.csv")

## Two definitions of column names
bincols1 <- c('bin_nInfC_n17C', 'bin_n17C_n12C', 'bin_n12C_n7C', 'bin_n7C_n2C', 'bin_n2C_3C', 'bin_3C_8C', 'bin_8C_13C', 'bin_13C_18C', 'bin_23C_28C', 'bin_28C_33C', 'bin_33C_InfC')
bincols2 <- c('bin_nInf_n17C', 'bin_n17C_n12C', 'bin_n12C_n7C', 'bin_n7C_n2C', 'bin_n2C_3C', 'bin_3C_8C', 'bin_8C_13C', 'bin_13C_18C', 'bin_23C_28C', 'bin_28C_33C', 'bin_33C_Inf')
meandaycols1 <- c('meandays_nInf_n17C', 'meandays_n17C_n12C', 'meandays_n12C_n7C', 'meandays_n7C_n2C', 'meandays_n2C_3C', 'meandays_3C_8C', 'meandays_8C_13C', 'meandays_13C_18C', 'meandays_23C_28C', 'meandays_28C_33C', 'meandays_33C_Inf')
meandaycols2 <- c('meandays_nInfC_n17C', 'meandays_n17C_n12C', 'meandays_n12C_n7C', 'meandays_n7C_n2C', 'meandays_n2C_3C', 'meandays_3C_8C', 'meandays_8C_13C', 'meandays_13C_18C', 'meandays_23C_28C', 'meandays_28C_33C', 'meandays_33C_InfC')


## Create a BayesObservations object to hold the data
bayeser <- BayeserObservations()

## Read all for which we have VCVs
supers <- integer()
for (ii in 1:length(adms)) {
    ## Read betas
    betas <- read.csv(paste(betadir, adms[ii], sep='/'), fileEncoding="latin1")
    betas$loggdppc <- log(betas$gdppc)
    betas$logpopop <- log(betas$popop)
    binbetas <- tryCatch({
        betas[, bincols1]
    }, error=function(e) {
        betas[, bincols2]
    })
    names(binbetas) <- bincols1

    ## Add observations and associated data to BayesObservations
    for (jj in 1:nrow(betas)) {
        if (ii <= length(dirs)) {
            ## Get the VCV
            file <- paste0(tolower(dirs[ii]), '_allage_state', betas$id[jj], '_VCV.csv')

            vcv <- read.csv(paste(basedir, dirs[ii], file, sep='/'))
            names(vcv) <- c("bin_nInfC_n17C", "bin_n17C_n12C", "bin_n12C_n7C", "bin_n7C_n2C", "bin_n2C_3C", "bin_3C_8C", "bin_8C_13C", "bin_13C_18C", "bin_23C_28C", "bin_28C_33C", "bin_33C_InfC")
            if (vcv[2, 3] != vcv[3, 2])
                error("not symmtric!")
        } else {
            ## Construct diagonal VCV
            vcv <- diag(as.numeric(betas[jj, c("se_nInfC_n17C", "se_n17C_n12C", "se_n12C_n7C", "se_n7C_n2C", "se_n2C_3C", "se_3C_8C", "se_8C_13C", "se_13C_18C", "se_23C_28C", "se_28C_33C", "se_33C_InfC")]))^2
            vcv[is.na(vcv)] <- 1
            names(vcv) <- c("bin_nInfC_n17C", "bin_n17C_n12C", "bin_n12C_n7C", "bin_n7C_n2C", "bin_n2C_3C", "bin_3C_8C", "bin_8C_13C", "bin_13C_18C", "bin_23C_28C", "bin_28C_33C", "bin_33C_InfC")
        }

        ## Construct a matrix of predictors
        predses <- matrix(0, 0, L)
        for (kk in 1:length(meandaycols1)) {
          row <- tryCatch({
              cbind(data.frame(const=1), betas[jj, c(meandaycols1[kk], 'logpopop', 'loggdppc')])
          }, error=function(e) {
              cbind(data.frame(const=1), betas[jj, c(meandaycols2[kk], 'logpopop', 'loggdppc')])
          })
          names(row) <- c('const', 'mdays', 'popop', 'gdppc')
          predses <- rbind(predses, row)
        }

        bayeser <- addObs(bayeser, binbetas[jj,], vcv, predses)
        supers <- c(supers, ii)
    }
}

## Fit the model for different smooths and save
binlos <- c(-Inf, -17, -12, -7, -2, 3, 8, 13, 23, 28, 33)
binhis <- c(-17, -12, -7, -2, 3, 8, 13, 18, 28, 33, Inf)

fit <- NULL

#for (smooth in c(2, 0, 4)) {
for (smooth in c(0)) {
  if (include.2stgfe) {
    fit <- estimate(bayeser, supers=supers)
  } else {
    fit <- estimate(bayeser)
  }

  print(fit)

  la <- extract(fit, permute=T)

  ## Output bin surface parameters
  result <- data.frame()
  for (kk in 1:K) {
      result <- rbind(result, data.frame(method='fullba', binlo=binlos[kk], binhi=binhis[kk],
                                         intercept_coef=mean(la$gamma[, kk, 1]),
                                         bindays_coef=mean(la$gamma[, kk, 2]),
                                         popop_coef=mean(la$gamma[, kk, 3]),
                                         gdppc_coef=mean(la$gamma[, kk, 4]),
                                         intercept_serr=sd(la$gamma[, kk, 1]),
                                         bindays_serr=sd(la$gamma[, kk, 2]),
                                         popop_serr=sd(la$gamma[, kk, 3]),
                                         gdppc_serr=sd(la$gamma[, kk, 4])))
  }
  
  if (include.2stgfe) {
    result_fe <- data.frame(apply(la$fes, c(2,3), mean))
    names(result_fe) = paste0(fe.units, "_fixeff")
    result <- cbind(result, result_fe)
    write.csv(result, paste0(spec, "_cntryfe_fullbayes", smooth, ".csv"), row.names=F)
  } else {
    write.csv(result, paste0(spec, "_fullbayes", smooth, ".csv"), row.names=F)
  }
}
