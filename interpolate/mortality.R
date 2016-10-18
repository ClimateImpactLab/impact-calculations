##setwd("~/research/gcp/impact-calculations/interpolate")

data.dir <- "../../data/adaptation"
source("mortality-helper.R")

## Test SUR
fit <- estimate.semur(surface)
summary(fit)

surface.write(surface, fit, "output.csvv", "Mortality stage 2 results", "MORTALITY-STAGE2", adms,
              paste(binlos, binhis, sep=" -- "), c('constant', 'meandays', 'logpopop', 'loggdppc'))

result <- data.frame()
for (kk in 1:11) {
    result <- rbind(result, data.frame(method='seemur', binlo=binlos[kk], binhi=binhis[kk],
                                       intercept_coef=fit$coeff[(kk-1)*4 + 1],
                                       bindays_coef=fit$coeff[(kk-1)*4 + 2],
                                       gdppc_coef=fit$coeff[(kk-1)*4 + 4],
                                       popop_coef=fit$coeff[(kk-1)*4 + 3],
                                       intercept_serr=sqrt(fit$coefCov[(kk-1)*4 + 1, (kk-1)*4 + 1]),
                                       bindays_serr=sqrt(fit$coefCov[(kk-1)*4 + 2, (kk-1)*4 + 2]),
                                       gdppc_serr=sqrt(fit$coefCov[(kk-1)*4 + 4, (kk-1)*4 + 4]),
                                       popop_serr=sqrt(fit$coefCov[(kk-1)*4 + 3, (kk-1)*4 + 3])))
}

write.csv(result, "seemur.csv", row.names=F)

## Test Bayesian
fit <- NULL

for (smooth in c(0, 1, 2, 4, 8)) {
    fit <- estimate.bayes(surface, smooth=smooth, dropbin=8, chains=20)

    print(fit)

    la <- extract(fit, permute=T)

    ## Output bin surface parameters
    result <- data.frame()
    for (kk in 1:11) {
        result <- rbind(result, data.frame(method='fullba', binlo=binlos[kk], binhi=binhis[kk],
                                           intercept_coef=mean(la$gamma[, kk, 1]),
                                           bindays_coef=mean(la$gamma[, kk, 2]),
                                           gdppc_coef=mean(la$gamma[, kk, 4]),
                                           popop_coef=mean(la$gamma[, kk, 3]),
                                           intercept_serr=sd(la$gamma[, kk, 1]),
                                           bindays_serr=sd(la$gamma[, kk, 2]),
                                           gdppc_serr=sd(la$gamma[, kk, 4]),
                                           popop_serr=sd(la$gamma[, kk, 3])))
    }

    write.csv(result, paste0("fullbayes", smooth, ".csv"), row.names=F)
}

surface.write(surface, fit, "output.csvv", "Mortality stage 2 results", "MORTALITY-STAGE2", adms,
              paste(binlos, binhis, sep=" -- "), c('constant', 'meandays', 'logpopop', 'loggdppc'))

as.latex(surface, fit)

if (F) {
bayesfit <- BayesianSurface(surface, fit, paste(binlos, binhis, sep=" -- "), c('constant', 'meandays', 'logpopop', 'loggdppc'))
texreg(bayesfit)
}
