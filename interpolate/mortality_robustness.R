##setwd("~/Repos/impact-calculations/interpolate")
##setwd("~/research/gcp/impact-calculations/interpolate")

data.dir <- "../../data/adaptation"
source("mortality-helper.R")

# Specification of 1st Stage model
K <- 11
spec <- "original"

# Specification of 2nd Stage model
L <- 4
include.2stgfe <- FALSE

fit <- NULL

#for (smooth in c(2, 0, 4)) {
for (smooth in c(0)) {
  if (include.2stgfe) {
    fit <- estimate.bayes(surface, stan.model.here=stan.model.fe, stan.data.extra=list("supers"=supers, "M"=max(supers)))
  } else {
    fit <- estimate.bayes(surface)
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
