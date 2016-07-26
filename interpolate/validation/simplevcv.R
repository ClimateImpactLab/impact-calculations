##setwd("~/research/gcp/impact-calculations/interpolate")

##for (do.serronly in c('BRA', 'CHN', 'IND', 'MEX')) {
do.serronly <- F

## Beta files
betadir <- "../../data/adaptation/inputs-apr-7"
adms <- c("BRA_adm1.csv", "CHN_adm1.csv", "IND_adm1.csv", "MEX_adm1.csv", "FRA_adm1.csv", "USA_adm1.csv")

## VCV files
basedir <- "../../data/adaptation/vcvs"
if (do.serronly == T) {
    dirs <- c()
} else if (do.serronly == 'BRA') {
    dirs <- c("BRAZIL")
} else if (do.serronly == 'CHN') {
    dirs <- c("CHINA")
    adms <- c("CHN_adm1.csv", "BRA_adm1.csv", "IND_adm1.csv", "MEX_adm1.csv", "FRA_adm1.csv", "USA_adm1.csv")
} else if (do.serronly == 'IND') {
    dirs <- c("INDIA")
    adms <- c("IND_adm1.csv", "CHN_adm1.csv", "BRA_adm1.csv", "MEX_adm1.csv", "FRA_adm1.csv", "USA_adm1.csv")
} else if (do.serronly == 'MEX') {
    dirs <- c("MEXICO")
    adms <- c("MEX_adm1.csv", "IND_adm1.csv", "CHN_adm1.csv", "BRA_adm1.csv", "FRA_adm1.csv", "USA_adm1.csv")
} else {
    dirs <- c("BRAZIL", "CHINA", "INDIA", "MEXICO")
}

allbetas <- matrix(0, 0, 11)
allvcv <- list()
allpreds <- list(matrix(0, 0, 4), matrix(0, 0, 4), matrix(0, 0, 4), matrix(0, 0, 4),
                 matrix(0, 0, 4), matrix(0, 0, 4), matrix(0, 0, 4), matrix(0, 0, 4),
                 matrix(0, 0, 4), matrix(0, 0, 4), matrix(0, 0, 4))

## Two definitions of column names
bincols1 <- c('bin_nInfC_n17C', 'bin_n17C_n12C', 'bin_n12C_n7C', 'bin_n7C_n2C', 'bin_n2C_3C', 'bin_3C_8C', 'bin_8C_13C', 'bin_13C_18C', 'bin_23C_28C', 'bin_28C_33C', 'bin_33C_InfC')
bincols2 <- c('bin_nInf_n17C', 'bin_n17C_n12C', 'bin_n12C_n7C', 'bin_n7C_n2C', 'bin_n2C_3C', 'bin_3C_8C', 'bin_8C_13C', 'bin_13C_18C', 'bin_23C_28C', 'bin_28C_33C', 'bin_33C_Inf')
meandaycols1 <- c('meandays_nInf_n17C', 'meandays_n17C_n12C', 'meandays_n12C_n7C', 'meandays_n7C_n2C', 'meandays_n2C_3C', 'meandays_3C_8C', 'meandays_8C_13C', 'meandays_13C_18C', 'meandays_23C_28C', 'meandays_28C_33C', 'meandays_33C_Inf')
meandaycols2 <- c('meandays_nInfC_n17C', 'meandays_n17C_n12C', 'meandays_n12C_n7C', 'meandays_n7C_n2C', 'meandays_n2C_3C', 'meandays_3C_8C', 'meandays_8C_13C', 'meandays_13C_18C', 'meandays_23C_28C', 'meandays_28C_33C', 'meandays_33C_InfC')

for (ii in 1:length(adms)) {
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
    allbetas <- rbind(allbetas, binbetas)

    ## Add observations and associated data to BayesObservations
    for (jj in 1:nrow(betas)) {
        if (ii <= length(dirs)) {
            ## Get the VCV
            file <- paste0(tolower(dirs[ii]), '_allage_state', betas$id[jj], '_VCV.csv')
            vcv <- read.csv(paste(basedir, dirs[ii], file, sep='/'))
            names(vcv) <- c("bin_nInfC_n17C", "bin_n17C_n12C", "bin_n12C_n7C", "bin_n7C_n2C", "bin_n2C_3C", "bin_3C_8C", "bin_8C_13C", "bin_13C_18C", "bin_23C_28C", "bin_28C_33C", "bin_33C_InfC")
            if (vcv[2, 3] != vcv[3, 2])
                error("not symmtric!")
        } else {
            ## Construct diagonal VCV
            vcv <- diag(tryCatch({
                as.numeric(betas[jj, c("se_nInfC_n17C", "se_n17C_n12C", "se_n12C_n7C", "se_n7C_n2C", "se_n2C_3C", "se_3C_8C", "se_8C_13C", "se_13C_18C", "se_23C_28C", "se_28C_33C", "se_33C_InfC")])
            }, error=function(e) {
                tryCatch({
                    as.numeric(betas[jj, c("se_nInfC_n17C", "se_n17C_n12C", "se_n12C_n7C", "se_n7C_n2C", "se_n2C_3C", "se_3C_8C", "se_8C_13C", "se_13C_18C", "se_23C_28C", "se_28C_33C", "se_33C_InfC_pop")])
                }, error=function(e) {
                    as.numeric(betas[jj, c("se_nInf_n17C", "se_n17C_n12C", "se_n12C_n7C", "se_n7C_n2C", "se_n2C_3C", "se_3C_8C", "se_8C_13C", "se_13C_18C", "se_23C_28C", "se_28C_33C", "se_33C_Inf")])
                })
            })^2)
            vcv[is.na(vcv)] <- Inf
            names(vcv) <- c("bin_nInfC_n17C", "bin_n17C_n12C", "bin_n12C_n7C", "bin_n7C_n2C", "bin_n2C_3C", "bin_3C_8C", "bin_8C_13C", "bin_13C_18C", "bin_23C_28C", "bin_28C_33C", "bin_33C_InfC")
        }

        allvcv[[length(allvcv)+1]] <- vcv
    }

    ## Construct a matrix of predictors
    for (kk in 1:length(meandaycols1)) {
        rows <- tryCatch({
            cbind(data.frame(const=1), betas[, c(meandaycols1[kk], 'logpopop', 'loggdppc')])
        }, error=function(e) {
            cbind(data.frame(const=1), betas[, c(meandaycols2[kk], 'logpopop', 'loggdppc')])
        })
        names(rows) <- c('const', 'mdays', 'popop', 'gdppc')
        allpreds[[kk]] <- rbind(allpreds[[kk]], rows)
    }
}

K <- 11
N <- nrow(allbetas)
L <- 4

allpreds2 <- array(0, c(K, N, 4))
for (jj in 1:K)
    allpreds2[jj, , ] <- as.matrix(allpreds[[jj]])

allvcv2 <- array(0, c(N, K, K))
for (ii in 1:N)
    allvcv2[ii, , ] <- as.matrix(allvcv[[ii]])

for (ii in 1:N)
    for (jj in 1:K)
        if (allvcv2[ii, jj, jj] == 0)
            allvcv2[ii, jj, jj] <- Inf

allbetas[is.na(allbetas)] <- 0

library(rstan)

binlos <- c(-Inf, -17, -12, -7, -2, 3, 8, 13, 23, 28, 33)
binhis <- c(-17, -12, -7, -2, 3, 8, 13, 18, 28, 33, Inf)

stan.data <- list(N=N, K=K, L=L, beta=t(allbetas[1:N,]), Sigma=allvcv2, x=allpreds2[, 1:N,])

save.fit <- function(fit, file) {
    la <- extract(fit, permute=T)

    result <- data.frame()
    for (kk in 1:11) {
        result <- rbind(result, data.frame(binlo=binlos[kk], binhi=binhis[kk],
                                           intercept_coef=mean(la$gamma[, kk, 1]),
                                           bindays_coef=mean(la$gamma[, kk, 2]),
                                           gdppc_coef=mean(la$gamma[, kk, 4]),
                                           popop_coef=mean(la$gamma[, kk, 3]),
                                           intercept_serr=sd(la$gamma[, kk, 1]),
                                           bindays_serr=sd(la$gamma[, kk, 2]),
                                           gdppc_serr=sd(la$gamma[, kk, 4]),
                                           popop_serr=sd(la$gamma[, kk, 3])))
    }

    write.csv(result, file, row.names=F)
}

## B-
stan.model.vcvpool <- "
data {
    int<lower=1> N; // number of study regions
    int<lower=1> K; // number of coefficients (not including dropped)
    int<lower=1> L; // number of predictors, including intercept

    vector[N] beta[K]; // estimated effects
    cov_matrix[K] Sigma[N]; // VCV across betas

    matrix[N, L] x[K]; // predictors across regions
}
transformed data {
    // Optimization: only compute decomposition once
    matrix[K, K] CholL[N];

    for (ii in 1:N)
      CholL[ii] <- cholesky_decompose(Sigma[ii]);
}
parameters {
    vector[L] gamma[K]; // surface parameters
}
transformed parameters {
    vector[K] predbeta[N];
    vector[K] transbeta[N];

    for (ii in 1:N)
      for (kk in 1:K) {
        predbeta[ii][kk] <- x[kk][ii] * gamma[kk];
        transbeta[ii][kk] <- beta[kk][ii];
      }
}
model {
    for (ii in 1:N)
      transbeta[ii] ~ multi_normal_cholesky(predbeta[ii], CholL[ii]);
}"

fit <- stan(model_code=stan.model.vcvpool, data=stan.data,
            iter = 1000, chains = 4)

if (do.serronly == T) {
    save.fit(fit, "simple-vcvpool-o-as-b.csv")
} else if (do.serronly == F) {
    save.fit(fit, "simple-vcvpool-bminus.csv")
} else {
    save.fit(fit, paste0("simple-vcvpool-bminus-", do.serronly, ".csv"))
}

}
