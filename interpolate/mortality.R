##setwd("~/research/gcp/impact-calculations/interpolate")

source("mortality-spline.R")

## Test SUR
fit <- estimate.semur(surface)
summary(fit)

sink("semur-spline.csvv-part")
cat("prednames\n")
cat(paste(prednames, collapse=','))
cat("\ncovarnames\n")
cat(paste(covarnames, collapse=','))
cat("\ngamma\n")
cat(paste(fit$coeff, collapse=','))
cat("\ngammavcv\n")
for (ii in 1:nrow(fit$coefCov)) {
    cat(paste(fit$coefCov[ii,], collapse=','))
    cat("\n")
}
sink()

## Test Bayesian
fit <- estimate.bayes(surface)
summary(fit)$summary[1:28,]

la = as.matrix(fit)
means <- colMeans(la[,1:21])
covs <- cov(la[,1:21])

prednames <- rep(paste0('term', 0:6), 3)
covarnames <- rep(c('1', 'loggdppc', 'tmean'), each=7)

sink("bayes-spline.csvv-part")
cat("prednames\n")
cat(paste(prednames, collapse=','))
cat("\ncovarnames\n")
cat(paste(covarnames, collapse=','))
cat("\ngamma\n")
cat(paste(means, collapse=','))
cat("\ngammavcv\n")
for (ii in 1:nrow(covs)) {
    cat(paste(covs[ii,], collapse=','))
    cat("\n")
}
sink()

mean.gdppc <- mean(betas$gdppc, na.rm=T)
mean.tmean <- mean(betas$Tmean_GMFD, na.rm=T)

source("~/research/gcp/hierarchical-estimation/display/from-csvv.R")
source("~/research/gcp/hierarchical-estimation/display/plotting.R")
source("~/research/gcp/hierarchical-estimation/display/splines.R")

xx <- seq(-15, 40, length.out=100)

yy <- read.csvv("semur-spline.csvv-part", paste0('term', 0:6), c('loggdppc', 'tmean'), c(log(mean.gdppc), mean.tmean), function(betas) pmax(-1e5, pmin(1e5, getspline(betas, xx))), mciters=1)

ggmedian(yy, xx)

df <- data.frame(x=c(), y=c(), group=c(), gdppc=c(), plausible=c())
for (ii in 1:nrow(betas)) {
    coeffs <- t(betas[ii, c('b_GMFD_term0_NS', 'b_GMFD_term1_NS', 'b_GMFD_term2_NS', 'b_GMFD_term3_NS', 'b_GMFD_term4_NS', 'b_GMFD_term5_NS', 'b_GMFD_term6_NS')])
    yy <- getspline(coeffs, xx) - getspline(coeffs, 20)
    plausible <- all(abs(yy) < 50)
    df <- rbind(df, data.frame(x=xx, y=yy, group=betas$region[ii], gdppc=betas$gdppc[ii], plausible))
}

ggplot(df, aes(x, y, group=group, colour=gdppc)) +
    geom_line() + ylim(-1e5, 1e5) +
    scale_colour_gradient(trans="log")

allpoints <- read.csvv("bayes-spline.csvv-part", paste0('term', 0:6), c('loggdppc', 'tmean'), c(log(mean.gdppc), mean.tmean), function(betas) pmax(-1e5, pmin(1e5, getspline(betas, xx) - getspline(betas, 20))), mciters=100)

ggstandard(allpoints, xx)

yy <- read.csvv("bayes-spline.csvv-part", paste0('term', 0:6), c('loggdppc', 'tmean'), c(log(mean.gdppc), mean.tmean), function(betas) pmin(1e5, getspline(betas, xx)), mciters=1)

ggmedian(yy, xx)


### END
exit()

surface.write(surface, fit, "output.csvv", "Mortality stage 2 results", "MORTALITY-STAGE2", adms,
              paste(binlos, binhis, sep=" -- "), c('constant', 'meandays', 'logpopop', 'loggdppc'))

as.latex(surface, fit)

if (F) {
bayesfit <- BayesianSurface(surface, fit, paste(binlos, binhis, sep=" -- "), c('constant', 'meandays', 'logpopop', 'loggdppc'))
texreg(bayesfit)
}
