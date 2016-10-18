## True generating process
gen <- function(const, w.lo, w.hi, wealth) {
    sensitivity <- 1 - wealth
    ##const + sensitivity * w.lo * .5 + sensitivity * w.hi + rnorm(length(w.lo))
    const + exp(sensitivity) * w.lo * .5 + exp(sensitivity) * w.hi + rnorm(length(w.lo))
}

randgen <- function(N, const, wealth) {
    w.hi <- runif(N, 0, 100)
    w.lo <- 100 - w.hi
    data.frame(w.lo, w.hi, wealth, y=gen(const, w.lo, w.hi, wealth))
}

N <- 1000
poor <- randgen(N, 10, .1)
poor$region <- "poor"
rich <- randgen(N, 10, .9)
rich$region <- "rich"

data <- rbind(poor, rich)
data$w.hi.wealth <- data$w.hi * data$wealth

summary(lm(y ~ factor(region) + w.hi + w.hi.wealth, data=data))

mod.poor <- lm(y ~ w.hi, data=poor)
mod.rich <- lm(y ~ w.hi, data=rich)

stan.model <- "
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

stan.data <- list(N=2, K=1, L=2, beta=matrix(c(mod.poor$coeff[2], mod.rich$coeff[2]), 2, 1),
                  Sigma=array(c(vcov(mod.poor)[2,2], vcov(mod.rich)[2,2]), c(2, 1, 1)),
                  x=array(c(1, 1, .1, .9), c(1, 2, 2)), x_dropped=matrix(c(1, 1, .1, .9), 2, 2))

library(rstan)

fit <- stan(model_code=stan.model, data=stan.data, iter=1000, chains=4)
