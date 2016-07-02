setwd("~/research/gcp/impact-calculations/interpolate")

library(MASS)
library(ggplot2)

## VCV files
basedir <- "../../data/adaptation/vcvs"
dirs <- c("BRAZIL", "CHINA", "INDIA", "MEXICO")

## Beta files-- may be longer than VCV list
betadir <- "../../data/adaptation/inputs-apr-7"
adms <- c("BRA_adm1.csv", "CHN_adm1.csv", "IND_adm1.csv", "MEX_adm1.csv")

## Two definitions of column names
bincols1 <- c('bin_nInfC_n17C', 'bin_n17C_n12C', 'bin_n12C_n7C', 'bin_n7C_n2C', 'bin_n2C_3C', 'bin_3C_8C', 'bin_8C_13C', 'bin_13C_18C', 'bin_23C_28C', 'bin_28C_33C', 'bin_33C_InfC')
bincols2 <- c('bin_nInf_n17C', 'bin_n17C_n12C', 'bin_n12C_n7C', 'bin_n7C_n2C', 'bin_n2C_3C', 'bin_3C_8C', 'bin_8C_13C', 'bin_13C_18C', 'bin_23C_28C', 'bin_28C_33C', 'bin_33C_Inf')
meandaycols1 <- c('meandays_nInf_n17C', 'meandays_n17C_n12C', 'meandays_n12C_n7C', 'meandays_n7C_n2C', 'meandays_n2C_3C', 'meandays_3C_8C', 'meandays_8C_13C', 'meandays_13C_18C', 'meandays_23C_28C', 'meandays_28C_33C', 'meandays_33C_Inf')
meandaycols2 <- c('meandays_nInfC_n17C', 'meandays_n17C_n12C', 'meandays_n12C_n7C', 'meandays_n7C_n2C', 'meandays_n2C_3C', 'meandays_3C_8C', 'meandays_8C_13C', 'meandays_13C_18C', 'meandays_23C_28C', 'meandays_28C_33C', 'meandays_33C_InfC')

##for (attempt in 1:10) {

ii <- sample(1:4, 1)

## Read betas
betas <- read.csv(paste(betadir, adms[ii], sep='/'))
betas$loggdppc <- log(betas$gdppc)
betas$logpopop <- log(betas$popop)
binbetas <- tryCatch({
    betas[, bincols1]
}, error=function(e) {
    betas[, bincols2]
})
names(binbetas) <- bincols1

jj <- sample(which(rowSums(!is.na(binbetas)) > 4), 1)

file <- paste0(tolower(dirs[ii]), '_allage_state', betas$id[jj], '_VCV.csv')

vcv <- read.csv(paste(basedir, dirs[ii], file, sep='/'))
names(vcv) <- c("bin_nInfC_n17C", "bin_n17C_n12C", "bin_n12C_n7C", "bin_n7C_n2C", "bin_n2C_3C", "bin_3C_8C", "bin_8C_13C", "bin_13C_18C", "bin_23C_28C", "bin_28C_33C", "bin_33C_InfC")
if (vcv[2, 3] != vcv[3, 2])
    error("not symmtric!")

## Fit the model for different smooths and save
binlos <- c(-Inf, -17, -12, -7, -2, 3, 8, 13, 23, 28, 33)
binhis <- c(-17, -12, -7, -2, 3, 8, 13, 18, 28, 33, Inf)
binxx <- (pmax(binlos, -22) + pmin(binhis, 38)) / 2

basic <- data.frame(xx=binxx,
                    yy=as.numeric(binbetas[jj, ]), serr=sqrt(diag(as.matrix(vcv))))

samples <- data.frame(xx=c(), yy=c(), group=c())
for (kk in 1:8) {
    yy <- mvrnorm(1, as.numeric(binbetas[jj, ]), as.matrix(vcv))
    yy <- c(yy[1:8], 0, yy[9:11])
    samples <- rbind(samples, data.frame(xx=c(binxx[1:8], 20.5, binxx[9:11]), yy=yy, group=kk))
}
samples$group <- factor(samples$group)

ylimmin <- max(-50, min(basic$yy - basic$serr * 1.96, na.rm=T))
ylimmax <- min(50, max(basic$yy + basic$serr * 1.96, na.rm=T))

print(ggplot(basic, aes(x=xx, y=yy)) +
    geom_point() +
    geom_errorbar(aes(ymin=yy + 1.96 * serr, ymax=yy - 1.96 * serr)) + geom_hline(yintercept=0) + theme_bw() +
    geom_line(data=samples, aes(x=xx, y=yy, colour=group, group=group)) +
    scale_x_continuous(name="Temperature bin") +
    coord_cartesian(ylim = c(ylimmin, ylimmax)) +
    scale_colour_manual(name="Draw:", values=c("#999999", "#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7")) +
    ggtitle(paste(dirs[ii], betas$region[jj])))

##cat ("Press [enter] to continue")
##line <- readline()
##}
