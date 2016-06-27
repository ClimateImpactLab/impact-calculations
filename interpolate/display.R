setwd("~/research/gcp/impact-calculations/interpolate")

library(reshape2)
library(ggplot2)

gammas0 <- read.csv("fullbayes0.csv")
gammas0$method <- "HBV Std. (AB+)"
#gammas4 <- read.csv("fullbayes4.csv")
#gammas4$method <- "fullba4"

gammas.x <- read.csv("seemur.csv")
gammas.x$method <- "SUR"

gammas <- rbind(gammas.x, gammas0)

pg <- melt(gammas[, c('method', 'binlo', 'binhi', 'intercept_coef', 'bindays_coef', 'gdppc_coef', 'popop_coef')], id.vars=c('method', 'binlo', 'binhi'))
pg2 <- melt(gammas[, c('method', 'binlo', 'binhi', 'intercept_serr', 'bindays_serr', 'gdppc_serr', 'popop_serr')], id.vars=c('method', 'binlo', 'binhi'))
pg$serr <- pg2$value

pg$binx <- (pmax(pg$binlo, -22) + pmin(pg$binhi, 38)) / 2
##pg$value[pg$variable == 'bindays_coef'] <- pg$value[pg$variable == 'bindays_coef'] * 20

dodge <- position_dodge(width=3)

pg$ymin <- pg$value - pg$serr
pg$ymax <- pg$value + pg$serr

levels(pg$variable) <- c("Intercept", "Days in bin", "GDP P.C.", "P.W. Pop. Dens.")

ggplot(subset(pg, variable != 'Intercept'), aes(x=binx, y=value, ymin=ymin, ymax=ymax, width=5, colour=method)) +
    facet_grid(variable ~ ., scales="free") +
    geom_point(position=dodge) +
    geom_errorbar(position=dodge) + geom_hline(yintercept=0) + theme_bw() +
    scale_x_continuous(name="") + scale_y_continuous(expand=c(0, 0)) +
    scale_colour_discrete(name="Method:") +
    theme(legend.position="top")
