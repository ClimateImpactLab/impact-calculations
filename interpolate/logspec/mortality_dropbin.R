setwd("~/research/gcp/impact-calculations/interpolate")

data.dir <- "../../data/adaptation"
source("mortality-helper.R")

stan.model.estl <- "
data {
    int<lower=1> N; // number of study regions
    int<lower=1> K; // number of coefficients (not including dropped)
    int<lower=1> L; // number of predictors, including intercept

    vector[K] beta[N]; // estimated effects
    cov_matrix[K] Sigma[N]; // VCV across betas

    matrix[N, L] x[K]; // predictors across regions
    matrix[N, L] x_dropped; // predictors across regions for dropped bin
}
transformed data {
    real maxbeta;

    // Optimization: only compute decomposition once
    matrix[K, K] CholL[N];
    for (ii in 1:N)
      CholL[ii] <- cholesky_decompose(Sigma[ii]);

    for (ii in 1:N)
      maxbeta <- fmax(maxbeta, max(beta[ii]));
}
parameters {
    vector[L] gamma[K]; // surface parameters
    real<lower=0> tau[K]; // variance in hyper equation
    vector<lower=0>[K] delta_theta[N]; // z-scores of true effects + baseline

    vector<lower=0>[N] baseline; // baseline value in coeff space, so all beta + baseline > 0
    vector[L] gamma_dropped;
    real<lower=0> tau_dropped;
}
transformed parameters {
    vector<lower=0>[N] delta_transtheta[K]; // transpose of delta_theta
    for (ii in 1:N) {
      for (kk in 1:K)
        delta_transtheta[kk][ii] <- delta_theta[ii][kk];
    }
}
model {
    baseline ~ lognormal(x_dropped * gamma_dropped, tau_dropped);

    // observed betas drawn from true parameters
    for (ii in 1:N)
       beta[ii] ~ multi_normal_cholesky(delta_theta[ii] - baseline[ii], CholL[ii]);

    // true parameters produced by linear expression
    for (kk in 1:K)
      increment_log_prob(lognormal_log(delta_transtheta[kk], x[kk] * gamma[kk], tau[kk]));
}"

## Test Bayesian
fit <- estimate.bayes(surface, stan.model.here=stan.model.estl, stan.data.extra=list("x_dropped"=dropped.preds), dropbin=8, chains=4)

fit <- estimate.bayes(surface, stan.model.here=stan.model.estl, stan.data.extra=list("x_dropped"=dropped.preds), dropbin=8, chains=4)

save(fit, file="mortality_dropbin.RData")
load("mortality_dropbin.RData")

library(rstan)
la <- extract(fit, permute=T)

library(reshape2)
library(ggplot2)

binlos <- c(-Inf, -17, -12, -7, -2, 3, 8, 13, 23, 28, 33)
binhis <- c(-17, -12, -7, -2, 3, 8, 13, 18, 28, 33, Inf)
predictors <- c("Intercept", "Days in Bin", "GDP P.C.", "P.W. Pop. Dens.")

df <- data.frame(binlo=c(), binhi=c(), predictor=c(), gamma=c(), sdev=c(), ismiss=c(), method=c())
for (ii in 1:length(binlos)) {
    for (jj in 1:4) {
        values <- la$gamma[, ii, jj]
        df <- rbind(df, data.frame(binlo=binlos[ii], binhi=binhis[ii], predictor=predictors[jj],
                                   gamma=mean(values), sdev=sd(values), ismiss=F, method="dropbin"))
    }
}
for (jj in 1:4) {
    values <- la$gamma_dropped[, jj]
    df <- rbind(df, data.frame(binlo=18, binhi=23, predictor=predictors[jj],
                               gamma=mean(la$gamma_dropped[, jj]), sdev=sd(values),
                               ismiss=T, method="dropbin"))
}

fullbayes0 <- read.csv("fullbayes0.csv")
seemur <- read.csv("seemur.csv")

for (ii in 1:nrow(fullbayes0))
    df <- rbind(df, data.frame(binlo=rep(fullbayes0$binlo, 4),
                               binhi=rep(fullbayes0$binhi, 4),
                               predictor=rep(predictors, each=nrow(fullbayes0)),
                               gamma=c(fullbayes0$intercept_coef, fullbayes0$bindays_coef,
                                       fullbayes0$gdppc_coef, fullbayes0$popop_coef),
                               sdev=c(fullbayes0$intercept_serr, fullbayes0$bindays_serr,
                                      fullbayes0$gdppc_serr, fullbayes0$popop_serr),
                               ismiss=F, method="fullbayes0"))

for (ii in 1:nrow(seemur))
    df <- rbind(df, data.frame(binlo=rep(seemur$binlo, 4),
                               binhi=rep(seemur$binhi, 4),
                               predictor=rep(predictors, each=nrow(seemur)),
                               gamma=c(seemur$intercept_coef, seemur$bindays_coef,
                                       seemur$gdppc_coef, seemur$popop_coef),
                               sdev=c(seemur$intercept_serr, seemur$bindays_serr,
                                      seemur$gdppc_serr, seemur$popop_serr),
                               ismiss=F, method="seemur"))

df$binx <- (df$binlo + df$binhi) / 2
df$binx[df$binx == -Inf] <- -19.5
df$binx[df$binx == Inf] <- 35.5
df$binx <- factor(df$binx)

ggplot(subset(df, method != "fullbayes0"), aes(x=binx, y=gamma, colour=method, linetype=ismiss)) +
    facet_grid(predictor ~ ., scales="free") +
    geom_point() +
    geom_errorbar(aes(ymin=gamma + sdev, ymax=gamma - sdev))
