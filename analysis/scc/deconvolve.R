setwd("~/research/gcp/socioeconomics/analysis/scc")

library(MASS)

## Assume that I have impacts file with columns year, cost

conc2ton <- 7.81e9 # 1 ppm = 2.13 GT C = 7.81 GT CO2
discountrate <- .03

do.equilibrium <- T
do.equiltrend <- T
do.smoothzero <- 1000 # 0 to remove
do.smoothing <- 10 # 0 to remove
do.smoothtrend <- 5000
do.subsets <- F

predyears <- 300

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

estimate <- function(XXs, yys) {
    ## Add intercept
    ## Divide all by 1e9 for computation
    XXs <- cbind(1, XXs / 1e9)
    yys <- yys / 1e9

    if (do.smoothing > 0) {
        ## Add regularization: smooth between impulse response, and last point of that and equilibrium
        if (do.smoothzero > 0) {
            XXs <- rbind(XXs, c(0, do.smoothzero, rep(0, delays + 1)))
            yys <- c(yys, 0)
        }

        ## Normal smoothing
        for (ii in 1:delays) {
            XXs <- rbind(XXs, do.smoothing * c(rep(0, ii), 1, -1, rep(0, delays + 1 - ii)))
            yys <- c(yys, 0)
        }

        if (do.smoothtrend > 0) {
            ## Smooth slope into next trend
            for (ii in 1:(delays - 1)) {
                ## h[N] - h[N-1] = h[N-1] - h[N-2]
                XXs <- rbind(XXs, do.smoothtrend * c(rep(0, ii), 1, -2, 1, rep(0, delays - ii)))
                yys <- c(yys, 0)
            }

            ## h[inf] - h[N] = slope
            XXs <- rbind(XXs, do.smoothtrend * c(rep(0, delays), -1, 1, -1))
            yys <- c(yys, 0)
        }
    }

    if (!do.equilibrium && !do.equiltrend) {
        ## Drop equilibrium response and trend
        XXs <- XXs[, 1:(ncol(XXs) - 2)]
    } else if (!do.equiltrend) {
        ## Drop equilibrium response
        XXs <- XXs[, 1:(ncol(XXs) - 1)]
    }

    beta.hat <- solve(t(XXs) %*% XXs) %*% t(XXs) %*% yys
    yys.hat <- XXs %*% beta.hat
    sigma2 <- sum((yys - yys.hat)^2) / (nrow(XXs) - ncol(XXs))
    vcv <- solve(t(XXs) %*% XXs) * sigma2
    ses <- sqrt(diag(vcv))

    list(beta.hat=beta.hat, ses=ses, vcv=vcv)
}

calcSCC <- function(beta.hat, ses, do.plot) {
    XXs <- cbind(0, tons2XXs(c(rep(0, 100), rep(1, predyears)), -99:predyears, 1:predyears))

    if (!do.equilibrium && !do.equiltrend) {
        ## Drop equilibrium response and trend
        XXs <- XXs[, 1:(ncol(XXs) - 2)]
    } else if (!do.equiltrend) {
        ## Drop equilibrium response
        XXs <- XXs[, 1:(ncol(XXs) - 1)]
    }

    predyys <- XXs %*% beta.hat

    if (do.plot) {
        library(ggplot2)
        predses <- XXs %*% ses

        print(ggplot(data.frame(year=1:predyears, cost=predyys, ses=predses), aes(x=year, y=cost)) +
              geom_bar(stat="identity") + geom_ribbon(aes(x=year - .5, ymin=cost - 1.96*ses, ymax=cost + 1.96*ses), alpha=.5) +
              xlab("Years since emission") + ylab("Cost ($)") +
              scale_x_continuous(limits=c(0, 100), expand=c(.01, 0)) + coord_cartesian(ylim=c(0, 26)) + theme_bw())

    }

    ## Construct a net present value
    sum(predyys / (1 + discountrate)^(0:(predyears - 1)))
}

yys <- c()
XXs <- matrix(NA, 0, delays + 2)

for (rcp in c('rcp45', 'rcp85')) {
    costs <- read.csv(paste0(rcp, "_monetized_results_avg_weighted.csv"))

    XX <- tons2XXs(co2concs[, rcp] * conc2ton, co2concs$year, costs$year)

    XXs <- rbind(XXs, XX)
    yys <- c(yys, costs[, costcol])
}

fit <- estimate(XXs, yys)
calcSCC(fit$beta.hat, fit$ses, T)

beta.hat <- mvrnorm(1000, fit$beta.hat, fit$vcv)
sccs <- c()
for (ii in 1:1000)
    sccs <- c(sccs, calcSCC(beta.hat[ii, ], NA, F))

c(mean(sccs), quantile(sccs, c(.025, .975)))

## Deconvolve for each set of 50 years

if (do.subsets) {
    yearspans <- 50

    results <- data.frame(rcp=c(), year=c(), scc=c(), cilo=c(), cihi=c())
    for (rcp in c('rcp45', 'rcp85')) {
        costs <- read.csv(paste0(rcp, "_monetized_results_avg_weighted.csv"))

        for (startyear in 2010:(2100 - yearspans)) {
            print(startyear)

            selectedrows <- costs$year >= startyear & costs$year < startyear + yearspans

            XXs <- tons2XXs(co2concs[, rcp] * conc2ton, co2concs$year, costs$year[selectedrows])
            yys <- c(costs[selectedrows, costcol])

            ## Add rows from the other RCP before 2060
            if (rcp == 'rcp45') {
                costs.other <- read.csv("rcp85_monetized_results_avg_weighted.csv")

                XXs2 <- tons2XXs(co2concs[, 'rcp85'] * conc2ton, co2concs$year, costs.other$year[costs.other$year < 2060])
                XXs <- rbind(XXs, XXs2)
                yys <- c(yys, costs.other[costs.other$year < 2060, costcol])
            } else if (rcp == 'rcp85') {
                costs.other <- read.csv("rcp45_monetized_results_avg_weighted.csv")

                XXs2 <- tons2XXs(co2concs[, 'rcp45'] * conc2ton, co2concs$year, costs.other$year[costs.other$year < 2060])
                XXs <- rbind(XXs, XXs2)
                yys <- c(yys, costs.other[costs.other$year < 2060, costcol])
            }

            scccis <- tryCatch({
                fit <- estimate(XXs, yys)
                ## Make multiple draws
                beta.hat <- mvrnorm(100, fit$beta.hat, fit$vcv)
                sccs <- c()
                for (ii in 1:100)
                    sccs <- c(sccs, calcSCC(beta.hat[ii, ], NA, F))

                c(mean(sccs), quantile(sccs, c(.025, .975)))
            }, error=function(e) {
                c(NA, NA, NA)
            })

            results <- rbind(results, data.frame(rcp, year=startyear, scc=scccis[1], cilo=scccis[2], cihi=scccis[3]))
        }
    }

    ggplot(results, aes(x=year, y=scc, colour=rcp)) +
        geom_line() + geom_ribbon(aes(ymin=cilo, ymax=cihi), alpha=.5) +
        xlab("") + ylab("Social cost of carbon ($ / ton CO2)") +
        scale_colour_discrete(name="", breaks=c("rcp45", "rcp85"), labels=c("RCP 4.5", "RCP 8.5")) +
        theme_bw() + scale_x_continuous(expand=c(0, 0)) +
        theme(legend.justification=c(0,1), legend.position=c(0,1))
}

