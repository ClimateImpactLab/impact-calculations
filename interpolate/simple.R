##setwd("~/research/gcp/impact-calculations/interpolate")

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
    vector[N] theta_z[K]; // z-scores of true effects
}
transformed parameters {
    vector[N] theta[K]; // true effects
    for (kk in 1:K)
      theta[kk] <- beta[kk] + sigma[kk] .* theta_z[kk];
}
model {
    // observed betas drawn from true parameters
    for (kk in 1:K) {
      theta_z[kk] ~ normal(0, 1);
      // implies: beta[kk] ~ normal(theta[kk], sigma[kk]);
    }
    // true parameters produced by linear expression
    for (kk in 1:K) {
      theta[kk] ~ normal(x[kk] * gamma[kk], tau[kk]);
    }
}"

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
        sigma <- as.numeric(betas[jj, c("se_nInfC_n17C", "se_n17C_n12C", "se_n12C_n7C", "se_n7C_n2C", "se_n2C_3C", "se_3C_8C", "se_8C_13C", "se_13C_18C", "se_23C_28C", "se_28C_33C", "se_33C_InfC")])
        sigma[is.na(sigma)] <- 1
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

fit <- stan(model_code=stan.model.novcv, data=stan.data,
                        iter = 1000, chains = 4)
