setwd("~/research/gcp/socioeconomics/analysis/scc")

## Assume that I have impacts file with columns year, cost

conc2ton <- 7.81e9 # 1 ppm = 2.13 GT C = 7.81 GT CO2
discountrate <- .03

do.equiltrend <- T
do.smoothing <- T

costcol <- "World_p500"

## Include 20-year transient, then linear response
## Based on http://www.gfdl.noaa.gov/blog/isaac-held/2014/09/03/50-volcanoes-and-the-transient-climate-response-part-ii/
delays <- 30

co2concs <- read.csv("co2conc.csv")

tons2XXs <- function(tons, tonyears, yyears) {
    XXs <- matrix(NA, 0, delays + 2)

    for (ii in 1:length(yyears)) {
        emits <- c(0, diff(tons))

        ## "Equilibrium" response
        posttrans <- tons[tonyears == yyears[ii] - delays]
        posttransyears <- (yyears[ii] - delays) - tonyears
        posttranstrend <- sum(posttransyears[posttransyears > 0] * emits[posttransyears > 0])

        ## "Transient" response
        beforepresent <- yyears[ii] - tonyears + 1
        beforeemits <- emits[beforepresent > 0 & beforepresent <= delays]

        XX <- c(rev(beforeemits), posttrans, posttranstrend)
        XXs <- rbind(XXs, XX)
    }

    row.names(XXs) <- 1:nrow(XXs)
    XXs
}

yys <- c()
XXs <- matrix(NA, 0, delays + 2)

for (rcp in c('rcp45', 'rcp85')) {
    costs <- read.csv(paste0(rcp, "_monetized_results_avg_weighted.csv"))

    XX <- tons2XXs(co2concs[, rcp] * conc2ton, co2concs$year, costs$year)

    XXs <- rbind(XXs, XX)
    yys <- c(yys, costs[, costcol])
}

## Add intercept
# Divide all by 1e9 for computation
XXs <- cbind(1, XXs / 1e9)
yys <- yys / 1e9

if (do.smoothing) {
    ## Add regularization: smooth between impulse response, and last point of that and equilibrium
    for (ii in 2:delays) { ## IDEA!  EMIT HAS OWN EFFECT
        XXs <- rbind(XXs, 100 * c(rep(0, ii), 1, -1, rep(0, delays + 1 - ii)))
        yys <- c(yys, 0)
    }
}

if (!do.equiltrend) {
    ## Drop equilibrium response
    XXs <- XXs[, 1:(ncol(XXs) - 2)]
}

beta.hat <- solve(t(XXs) %*% XXs) %*% t(XXs) %*% yys
yys.hat <- XXs %*% beta.hat
sigma2 <- sum((yys - yys.hat)^2) / (nrow(XXs) - ncol(XXs))
vcv <- solve(t(XXs) %*% XXs) * sigma2
ses <- sqrt(diag(vcv))

predXXs <- cbind(0, tons2XXs(c(rep(0, 100), rep(1, 150)), -99:150, 1:150))

if (!do.equiltrend) {
    ## Drop equilibrium response
    predXXs <- predXXs[, 1:(ncol(predXXs) - 2)]
}

predyys <- predXXs %*% beta.hat

library(ggplot2)
ggplot(data.frame(year=1:150, cost=predyys), aes(x=year, y=cost)) +
    geom_bar(stat="identity") +
    xlab("Years since emission") + ylab("Cost ($)") +
    scale_x_continuous(limits=c(0, 100)) + theme_bw()

## Construct a net present value
sum(predyys / (1 + discountrate)^(0:149))
