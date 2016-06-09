setwd("~/research/gcp/impact-calculations/adaptation/surface")

library(reshape2)
library(ggplot2)

gammas0 <- read.csv("fullbayes0.csv")
gammas0$method <- "fullba0"
gammas4 <- read.csv("fullbayes4.csv")
gammas4$method <- "fullba4"
gammas <- rbind(read.csv("comparison-all.csv"), gammas0, gammas4)

pg <- melt(gammas[gammas$method != 'montec', c('method', 'binlo', 'binhi', 'intercept_coef', 'bindays_coef', 'gdppc_coef', 'popop_coef')], id.vars=c('method', 'binlo', 'binhi'))
pg2 <- melt(gammas[gammas$method != 'montec', c('method', 'binlo', 'binhi', 'intercept_serr', 'bindays_serr', 'gdppc_serr', 'popop_serr')], id.vars=c('method', 'binlo', 'binhi'))
pg$serr <- pg2$value

pg$binx <- (pmax(pg$binlo, -22) + pmin(pg$binhi, 38)) / 2
##pg$value[pg$variable == 'bindays_coef'] <- pg$value[pg$variable == 'bindays_coef'] * 20

dodge <- position_dodge(width=3)

pg$ymin <- pg$value - pg$serr
pg$ymax <- pg$value + pg$serr
pg$ymin[pg$variable == 'gdppc_coef' & pg$ymin < -6] <- -6
pg$ymax[pg$variable == 'gdppc_coef' & pg$ymax > 7] <- 7
pg$ymin[pg$variable == 'popop_coef' & pg$ymin < -6] <- -4
pg$ymax[pg$variable == 'popop_coef' & pg$ymax > 7] <- 7

levels(pg$method) <- c("Beta-only hier. reg.", "Monte Carlo", "Pooled", "SUR", "Unsmoothed hier. reg.", "Smoothed hier. reg.")
levels(pg$variable) <- c("Intercept", "Days in bin", "GDP P.C.", "P.W. Pop. Dens.")

ggplot(subset(pg, variable != 'Intercept'), aes(x=binx, y=value, ymin=ymin, ymax=ymax, width=5, colour=method)) +
    facet_grid(variable ~ ., scales="free") +
    geom_point(position=dodge) +
    geom_errorbar(position=dodge) + geom_hline(yintercept=0) + theme_bw() +
    scale_x_continuous(name="") + scale_y_continuous(expand=c(0, 0)) +
    scale_colour_discrete(name="Method:") +
    theme(legend.position="top")
