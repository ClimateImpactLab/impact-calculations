setwd("~/research/gcp/impact-calculations/interpolate/validation")

library(reshape2)
library(ggplot2)

do.smooth <- F

gammas.om <- read.csv("simple-serrpool-ominus.csv")
gammas.om$method <- "SE Pool (O-)"
gammas.am <- read.csv("simple-novcv-aminus.csv")
gammas.am$method <- "SE Hierarchical (A-)"
gammas.bm <- read.csv("simple-vcvpool-bminus.csv")
gammas.bm$method <- "VCV Pool (B-)"
gammas.ob <- read.csv("simple-vcvpool-o-as-b.csv")
gammas.ob$method <- "SE Pool using VCV Pool Model (O-)"
gammas.bm.bra <- read.csv("simple-vcvpool-bminus-BRA.csv")
gammas.bm.bra$method <- "Brazil VCV (B-)"
gammas.bm.chn <- read.csv("simple-vcvpool-bminus-CHN.csv")
gammas.bm.chn$method <- "China VCV (B-)"
gammas.bm.ind <- read.csv("simple-vcvpool-bminus-IND.csv")
gammas.bm.ind$method <- "India VCV (B-)"
gammas.bm.mex <- read.csv("simple-vcvpool-bminus-MEX.csv")
gammas.bm.mex$method <- "Mexico VCV (B-)"

##gammas.x <- subset(read.csv("comparison-all.csv"), method == 'seemur')
gammas.x <- read.csv("seemur.csv")
gammas.x$method <- "SUR"

gammas.op1 <- read.csv("simple-serrsmooth-oplus1.csv")
gammas.op1$method <- "SE Pool (O+1)"
gammas.op2 <- read.csv("simple-serrsmooth-oplus2.csv")
gammas.op2$method <- "SE Pool (O+2)"
gammas.op4 <- read.csv("simple-serrsmooth-oplus4.csv")
gammas.op4$method <- "SE Pool (O+4)"
gammas.op8 <- read.csv("simple-serrsmooth-oplus8.csv")
gammas.op8$method <- "SE Pool (O+8)"

if (do.smooth) {
    gammas <- rbind(gammas.om, gammas.op1, gammas.op2, gammas.op4, gammas.op8)
} else {
    gammas <- rbind(gammas.x, gammas.bm.bra, gammas.bm.chn, gammas.bm.ind, gammas.bm.mex, gammas.bm)
    ##gammas <- rbind(gammas.om, gammas.ob)

    gammas$method <- factor(gammas$method, levels=c(unique(gammas$method[gammas$method != "SUR"]), "SUR"))
}


pg <- melt(gammas[, c('method', 'binlo', 'binhi', 'intercept_coef', 'bindays_coef', 'gdppc_coef', 'popop_coef')], id.vars=c('method', 'binlo', 'binhi'))
pg2 <- melt(gammas[, c('method', 'binlo', 'binhi', 'intercept_serr', 'bindays_serr', 'gdppc_serr', 'popop_serr')], id.vars=c('method', 'binlo', 'binhi'))
pg$serr <- pg2$value

pg$binx <- (pmax(pg$binlo, -22) + pmin(pg$binhi, 38)) / 2

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
