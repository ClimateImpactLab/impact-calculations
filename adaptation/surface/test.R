##setwd("~/research/gcp/impact-calculations/adaptation/surface")

source("bayeser.R")

bayeser <- BayeserObservations()

## Read all values
basedir <- "../../../data/adaptation/vcvs"
dirs <- c("BRAZIL", "CHINA", "INDIA", "MEXICO")

betadir <- "../../../data/adaptation/inputs-apr-7"
adms <- c("BRA_adm1.csv", "CHN_adm1.csv", "IND_adm1.csv", "MEX_adm1.csv", "FRA_adm1.csv", "USA_adm1.csv")

bincols1 <- c('bin_nInfC_n17C', 'bin_n17C_n12C', 'bin_n12C_n7C', 'bin_n7C_n2C', 'bin_n2C_3C', 'bin_3C_8C', 'bin_8C_13C', 'bin_13C_18C', 'bin_23C_28C', 'bin_28C_33C', 'bin_33C_InfC')
bincols2 <- c('bin_nInf_n17C', 'bin_n17C_n12C', 'bin_n12C_n7C', 'bin_n7C_n2C', 'bin_n2C_3C', 'bin_3C_8C', 'bin_8C_13C', 'bin_13C_18C', 'bin_23C_28C', 'bin_28C_33C', 'bin_33C_Inf')
meandaycols1 <- c('meandays_nInf_n17C', 'meandays_n17C_n12C', 'meandays_n12C_n7C', 'meandays_n7C_n2C', 'meandays_n2C_3C', 'meandays_3C_8C', 'meandays_8C_13C', 'meandays_13C_18C', 'meandays_23C_28C', 'meandays_28C_33C', 'meandays_33C_Inf')
meandaycols2 <- c('meandays_nInfC_n17C', 'meandays_n17C_n12C', 'meandays_n12C_n7C', 'meandays_n7C_n2C', 'meandays_n2C_3C', 'meandays_3C_8C', 'meandays_8C_13C', 'meandays_13C_18C', 'meandays_23C_28C', 'meandays_28C_33C', 'meandays_33C_InfC')

for (ii in 1:length(dirs)) {
    betas <- read.csv(paste(betadir, adms[ii], sep='/'))
    betas$loggdppc <- log(betas$gdppc)
    betas$logpopop <- log(betas$popop)
    binbetas <- tryCatch({
        betas[, bincols1]
    }, error=function(e) {
        betas[, bincols2]
    })
    names(binbetas) <- bincols1

    for (jj in 1:nrow(betas)) {
        file <- paste0(tolower(dirs[ii]), '_allage_state', betas$id[jj], '_VCV.csv')

        vcv <- read.csv(paste(basedir, dirs[ii], file, sep='/'))
        names(vcv) <- c("bin_nInfC_n17C", "bin_n17C_n12C", "bin_n12C_n7C", "bin_n7C_n2C", "bin_n2C_3C", "bin_3C_8C", "bin_8C_13C", "bin_13C_18C", "bin_23C_28C", "bin_28C_33C", "bin_33C_InfC")
        if (vcv[2, 3] != vcv[3, 2])
            error("not symmtric!")
        allvcv[[length(allvcv)+1]] <- vcv

        predses <- matrix(0, 0, 4)
        for (kk in 1:length(meandaycols1)) {
            row <- tryCatch({
                cbind(data.frame(const=1), betas[jj, c(meandaycols1[kk], 'logpopop', 'loggdppc')])
            }, error=function(e) {
                cbind(data.frame(const=1), betas[jj, c(meandaycols2[kk], 'logpopop', 'loggdppc')])
            })
            names(row) <- c('const', 'mdays', 'popop', 'gdppc')
            predses <- rbind(predses, row)
        }

        bayeser <- addObs(bayeser, binbetas[jj,], vcv, predses)
    }
}

if (length(adms) > length(dirs)) {
    for (ii in (length(dirs) + 1):length(adms)) {
        betas <- read.csv(paste(betadir, adms[ii], sep='/'))
        betas$loggdppc <- log(betas$gdppc)
        betas$logpopop <- log(betas$popop)
        binbetas <- tryCatch({
            betas[, bincols1]
        }, error=function(e) {
            betas[, bincols2]
        })
        names(binbetas) <- bincols1

        for (jj in 1:nrow(betas)) {
            vcv <- diag(as.numeric(betas[jj, c("se_nInfC_n17C", "se_n17C_n12C", "se_n12C_n7C", "se_n7C_n2C", "se_n2C_3C", "se_3C_8C", "se_8C_13C", "se_13C_18C", "se_23C_28C", "se_28C_33C", "se_33C_InfC")]))
            vcv[is.na(vcv)] <- 1
            names(vcv) <- c("bin_nInfC_n17C", "bin_n17C_n12C", "bin_n12C_n7C", "bin_n7C_n2C", "bin_n2C_3C", "bin_3C_8C", "bin_8C_13C", "bin_13C_18C", "bin_23C_28C", "bin_28C_33C", "bin_33C_InfC")

            predses <- matrix(0, 0, 4)
            for (kk in 1:length(meandaycols1)) {
                row <- tryCatch({
                    cbind(data.frame(const=1), betas[jj, c(meandaycols1[kk], 'logpopop', 'loggdppc')])
                }, error=function(e) {
                    cbind(data.frame(const=1), betas[jj, c(meandaycols2[kk], 'logpopop', 'loggdppc')])
                })
                names(row) <- c('const', 'mdays', 'popop', 'gdppc')
                predses <- rbind(predses, row)
            }

            bayeser <- addObs(bayeser, binbetas[jj,], vcv, predses)
        }
    }
}

binlos <- c(-Inf, -17, -12, -7, -2, 3, 8, 13, 23, 28, 33)
binhis <- c(-17, -12, -7, -2, 3, 8, 13, 18, 28, 33, Inf)

fit <- NULL

for (smooth in c(2, 0, 4)) {
    fit <- estimate(bayeser)

    print(fit)

    la <- extract(fit, permute=T)

    ## Output bin surface parameters
    result <- data.frame()
    for (kk in 1:K) {
        result <- rbind(result, data.frame(method='fullba', binlo=binlos[kk], binhi=binhis[kk],
                                           intercept_coef=mean(la$gamma[, kk, 1]),
                                           bindays_coef=mean(la$gamma[, kk, 2]),
                                           gdppc_coef=mean(la$gamma[, kk, 3]),
                                           popop_coef=mean(la$gamma[, kk, 4]),
                                           intercept_serr=sd(la$gamma[, kk, 1]),
                                           bindays_serr=sd(la$gamma[, kk, 2]),
                                           gdppc_serr=sd(la$gamma[, kk, 3]),
                                           popop_serr=sd(la$gamma[, kk, 4])))
    }

    write.csv(result, paste0("fullbayes", smooth, ".csv"), row.names=F)
}

library(ggplot2)

## Curious about covariance
data <- data.frame(bin=rep(1:11, times=2000), gamma=c(la$gamma[, 1, 1], la$gamma[, 2, 1], la$gamma[, 3, 1], la$gamma[, 4, 1], la$gamma[, 5, 1], la$gamma[, 6, 1], la$gamma[, 7, 1], la$gamma[, 8, 1], la$gamma[, 9, 1], la$gamma[, 10, 1], la$gamma[, 11, 1]), group=rep(1:2000, 11))

ggplot(data, aes(x=bin, y=gamma, group=group, colour=group)) +
    geom_line(alpha=.1) + scale_x_continuous(expand=c(0, 0)) + ylim(-1, 1)

data <- data.frame()
for (bin in 1:11)
    for (pred in 1:4) {
        data <- rbind(data, data.frame(bin, pred, mean=mean(la$gamma[, bin, pred]), sd=sd(la$gamma[, bin, pred])))
    }

ggplot(data, aes(x=bin, y=mean)) +
    facet_grid(pred ~ ., scales="free") +
    geom_point()

ggplot(data, aes(x=bin, y=mean, ymin=mean - sd, max=mean + sd)) +
    facet_grid(pred ~ ., scales="free") +
    geom_errorbar()
