setwd("~/projects/dmas/ext/gcp/data/adaptation")

source("../../src/helpers/header.R")

## Excerpts from the outputs from DMAS

## Predictors:
## region,year,bin0,bin1,bin2,bin3,bin4,bin5,bin6,bin7,bin8,bin9,bin10,bin11,gdppc,popop
## BOL.4.33.101,1981,0.0,0.0,0.0,0.0,0.0,33.54,248.05,83.41,0.0,0.0,0.0,8.2898219847100485,3.2780378852667642

## Interpolated model and result
## region,year,result,model,bin0,bin1,bin2,bin3,bin4,bin5,bin6,bin7,bin8,bin9,bin10,bin11
## BOL.4.33.101,1981,all,0.00035075754469978283,113.45767719876727,113.45767719876727,42.943188912024269,12.515892501759033,5.0610811527987885,1.6295532634731078,-0.17176512165639846,0.79296157831143099,nan,0.62167733474470888,3.0400692662389464,54.374288704695616

## Check that all bin coefficients are correct

## Bolivia to be fed into the surface, after it's estimated (copied from above)
predictors <- c(1.,0.0,0.0,0.0,0.0,0.0038152042447694586,34.2620419993582,244.98297401421115,85.75116878218581,0.0,0.0,0.0,8.2898219847100485,3.3090168916970475)
## Results from DMAS, for comparison (copied from above)
dmasbins <- c(113.45767719876727,113.45767719876727,42.943188912024269,12.515892501759033,5.0610811527987885,1.6295532634731078,-0.17176512165639846,0.79296157831143099,0.62167733474470888,3.0400692662389464,54.374288704695616)

## All the files to read
binfiles <- c('bin_ninfC_n17.0C.csv', 'bin_n17.0C_n12.0C.csv', 'bin_n12.0C_n7.0C.csv', 'bin_n7.0C_n2.0C.csv', 'bin_n2.0C_3.0C.csv', 'bin_3.0C_8.0C.csv', 'bin_8.0C_13.0C.csv', 'bin_13.0C_18.0C.csv', 'bin_23.0C_28.0C.csv', 'bin_28.0C_33.0C.csv', 'bin_33.0C_infC.csv')

results <- data.frame(bin=c(), dmas=c(), calc=c(), gdppccoef=c(), popopcoef=c())

## For each bin, estimate the surface
for (ii in 1:length(binfiles)) {
    ## Prepare all the points on the surface
    data <- read.csv(header.deparse(paste0("predictors-space-all/", binfiles[ii])))
    data$loggdppc <- log(data$gdppc)
    data$logpopop <- log(data$popop)
    data$serr[data$serr == 0] <- NA

    ## Estimate the model, with a single intercept
    mod <- lm(coef ~ meandays_nInfC_n17C + meandays_n17C_n12C + meandays_n12C_n7C + meandays_n7C_n2C + meandays_n2C_3C + meandays_3C_8C + meandays_8C_13C + meandays_13C_18C + meandays_23C_28C + meandays_28C_33C + meandays_33C_InfC + loggdppc + logpopop, weights=1/(serr^2), data=data)

    ## Apply the coefficients to our predictors
    calc <- sum(mod$coefficients * predictors)
    dmas <- dmasbins[ii]

    gdppccoef <- mod$coefficients[length(mod$coefficients)-1]
    popopcoef <- mod$coefficients[length(mod$coefficients)]

    ## Build up a data.frame of the results
    results <- rbind(results, data.frame(bin=binfiles[ii], dmas, calc, gdppccoef, popopcoef))
}

## View the comparison
results
