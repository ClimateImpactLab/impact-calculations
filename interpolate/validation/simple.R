##setwd("~/research/gcp/impact-calculations/interpolate")

allbetas <- matrix(0, 0, 11)
allsigma <- matrix(0, 0, 11)
allpreds <- list(matrix(0, 0, 4), matrix(0, 0, 4), matrix(0, 0, 4), matrix(0, 0, 4),
                 matrix(0, 0, 4), matrix(0, 0, 4), matrix(0, 0, 4), matrix(0, 0, 4),
                 matrix(0, 0, 4), matrix(0, 0, 4), matrix(0, 0, 4))

## Beta files
betadir <- "../../data/adaptation/inputs-apr-7"
adms <- c("BRA_adm1.csv", "CHN_adm1.csv", "IND_adm1.csv", "MEX_adm1.csv", "FRA_adm1.csv", "USA_adm1.csv")

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
        ## Construct diagonal VCV
        sigma <- tryCatch({
            as.numeric(betas[jj, c("se_nInfC_n17C", "se_n17C_n12C", "se_n12C_n7C", "se_n7C_n2C", "se_n2C_3C", "se_3C_8C", "se_8C_13C", "se_13C_18C", "se_23C_28C", "se_28C_33C", "se_33C_InfC")])
        }, error=function(e) {
            tryCatch({
                as.numeric(betas[jj, c("se_nInfC_n17C", "se_n17C_n12C", "se_n12C_n7C", "se_n7C_n2C", "se_n2C_3C", "se_3C_8C", "se_8C_13C", "se_13C_18C", "se_23C_28C", "se_28C_33C", "se_33C_InfC_pop")])
            }, error=function(e) {
                as.numeric(betas[jj, c("se_nInf_n17C", "se_n17C_n12C", "se_n12C_n7C", "se_n7C_n2C", "se_n2C_3C", "se_3C_8C", "se_8C_13C", "se_13C_18C", "se_23C_28C", "se_28C_33C", "se_33C_Inf")])
            })
        })
        sigma[is.na(sigma)] <- Inf
        names(sigma) <- c("bin_nInfC_n17C", "bin_n17C_n12C", "bin_n12C_n7C", "bin_n7C_n2C", "bin_n2C_3C", "bin_3C_8C", "bin_8C_13C", "bin_13C_18C", "bin_23C_28C", "bin_28C_33C", "bin_33C_InfC")
        allsigma <- rbind(allsigma, sigma)
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

allbetas[is.na(allbetas)] <- 0

library(rstan)

binlos <- c(-Inf, -17, -12, -7, -2, 3, 8, 13, 23, 28, 33)
binhis <- c(-17, -12, -7, -2, 3, 8, 13, 18, 28, 33, Inf)

stan.data <- list(N=N, K=K, L=L, beta=t(allbetas[1:N,]), sigma=t(allsigma[1:N,]), x=allpreds2[, 1:N,])

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

## A-
stan.model.novcv.subset <- "
data {
    int<lower=1> N; // number of study regions
    int<lower=1> K; // number of coefficients (not including dropped)
    int<lower=1> L; // number of predictors, including intercept

    vector[N] beta[K]; // estimated effects
    vector[N] sigma[K]; // std. errors for the betas
    matrix[N, L] x[K]; // predictors across regions
}
transformed data {
    int<lower=0> theta_index[N, K];
    int<lower=0> valid_count;

    valid_count <- 0;
    for (ii in 1:N)
      for (kk in 1:K) {
        if (sigma[kk][ii] != positive_infinity()) {
          valid_count <- valid_count + 1;
          theta_index[ii, kk] <- valid_count;
        } else
          theta_index[ii, kk] <- 0;
      }
}
parameters {
    vector[L] gamma[K]; // surface parameters
    real<lower=0> tau[K]; // variance in hyper equation
    real theta_z[valid_count];
}
transformed parameters {
    vector[N] theta[K]; // true effects
    for (ii in 1:N)
      for (kk in 1:K) {
        if (theta_index[ii, kk] == 0)
          theta[kk][ii] <- 0;
        else
          theta[kk][ii] <- theta_z[theta_index[ii, kk]];
      }
}
model {
    // observed betas drawn from true parameters
    theta_z ~ normal(0, 1);
    // true parameters produced by linear expression
    for (kk in 1:K) {
      theta[kk] ~ normal(x[kk] * gamma[kk], tau[kk]);
    }
}"

stan.model.novcv <- "
data {
    int<lower=1> N; // number of study regions
    int<lower=1> K; // number of coefficients (not including dropped)
    int<lower=1> L; // number of predictors, including intercept

    vector[N] beta[K]; // estimated effects
    vector[N] sigma[K]; // std. errors for the betas
    matrix[N, L] x[K]; // predictors across regions
}
parameters {
    vector[L] gamma[K]; // surface parameters
    real<lower=0> tau[K]; // variance in hyper equation
    vector[N] theta[K]; // true effects
    //vector[N] theta_z[K]; // z-scores of true effects
}
model {
    // observed betas drawn from true parameters
    for (kk in 1:K)
      beta[kk] ~ normal(theta[kk], sigma[kk]);
    // true parameters produced by linear expression
    for (kk in 1:K) {
      theta[kk] ~ normal(x[kk] * gamma[kk], tau[kk]);
    }
}"

fit <- stan(model_code=stan.model.novcv, data=stan.data,
            iter = 1000, chains = 4)

save.fit(fit, "simple-novcv-aminus.csv")

## O-
stan.model.serrpool <- "
data {
    int<lower=1> N; // number of study regions
    int<lower=1> K; // number of coefficients (not including dropped)
    int<lower=1> L; // number of predictors, including intercept

    vector[N] beta[K]; // estimated effects
    vector[N] sigma[K]; // std. errors for the betas
    matrix[N, L] x[K]; // predictors across regions
}
parameters {
    vector[L] gamma[K]; // surface parameters
    real<lower=0> tau[K]; // error scale
}
model {
    for (kk in 1:K) {
      beta[kk] ./ sigma[kk] ~ normal((x[kk] * gamma[kk]) ./ sigma[kk], tau[kk]);
    }
}"

fit <- stan(model_code=stan.model.serrpool, data=stan.data,
            iter = 1000, chains = 4)

save.fit(fit, "simple-serrpool-ominus.csv")

# O+
stan.model.serrsmooth <- "
data {
    int<lower=1> N; // number of study regions
    int<lower=1> K; // number of coefficients (not including dropped)
    int<lower=1> L; // number of predictors, including intercept

    vector[N] beta[K]; // estimated effects
    vector[N] sigma[K]; // std. errors for the betas

    matrix[N, L] x[K]; // predictors across regions

    real<lower=0> smooth; // prior on second derivative
    int<lower=0> dropbin; // index of dropped bin
}
parameters {
    vector[L] gamma[K]; // surface parameters
    real<lower=0> tau[K]; // error scale
}
model {
    for (ii in 1:L)
      for (kk in 3:(K+1)) {
        if (kk < dropbin)
          2 * gamma[kk-1][ii] - gamma[kk][ii] - gamma[kk-2][ii] ~ normal(0, 1 / smooth);
        else if (kk == dropbin)
          2 * gamma[kk-1][ii] - gamma[kk-2][ii] ~ normal(0, 1 / smooth);
        else if (kk == dropbin + 1)
          - gamma[kk-1][ii] - gamma[kk-2][ii] ~ normal(0, 1 / smooth);
        else if (kk == dropbin + 2)
          2 * gamma[kk-2][ii] - gamma[kk-1][ii] ~ normal(0, 1 / smooth);
        else
          2 * gamma[kk-2][ii] - gamma[kk-1][ii] - gamma[kk-3][ii] ~ normal(0, 1 / smooth);
      }

    for (kk in 1:K) {
      beta[kk] ./ sigma[kk] ~ normal((x[kk] * gamma[kk]) ./ sigma[kk], tau[kk]);
    }
}"

fit <- NA
for (smooth in c(1, 2, 4, 8)) {

    stan.data[["smooth"]] <- smooth
    stan.data[["dropbin"]] <- 8

    if (is.na(fit))
        fit <- stan(model_code=stan.model.serrsmooth, data=stan.data,
                    iter = 1000, chains = 4)
    else
        fit <- stan(fit=fit, data=stan.data,
                    iter = 1000, chains = 4)

    save.fit(fit, paste0("simple-serrsmooth-oplus", smooth, ".csv"))
}
