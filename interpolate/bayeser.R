library(methods)
library(matrixStats)
library(rstan)

stan.model <- "
data {
    int<lower=1> N; // number of study regions
    int<lower=1> K; // number of coefficients (not including dropped)
    int<lower=1> L; // number of predictors, including intercept

    vector[K] beta[N]; // estimated effects
    cov_matrix[K] Sigma[N]; // VCV across betas

    matrix[N, L] x[K]; // predictors across regions

    real<lower=0> smooth; // prior on second derivative
    int<lower=0> dropbin; // index of dropped bin

    real<lower=0> maxsigma; // upper limit on sigma
    real<lower=0> maxgamma; // limits on gamma
}
transformed data {
    // Optimization: only compute decomposition once
    matrix[K, K] CholL[N];
    for (ii in 1:N)
      CholL[ii] <- cholesky_decompose(Sigma[ii]);
}
parameters {
    vector<lower=-maxgamma, upper=maxgamma>[L] gamma[K]; // surface parameters
    real<lower=0, upper=maxsigma> tau[K]; // variance in hyper equation
    vector[K] theta_z[N]; // z-scores of true effects
}
transformed parameters {
    vector[K] theta[N]; // true effects
    vector[N] transtheta[K]; // transpose of theta
    for (ii in 1:N) {
      theta[ii] <- beta[ii] + CholL[ii] * theta_z[ii];
      for (kk in 1:K)
        transtheta[kk][ii] <- theta[ii][kk];
    }
}
model {
    // Add on the priors
    if (smooth > 0) {
      for (ii in 1:N)
        for (kk in 3:(K+1)) {
          if (kk < dropbin)
            2 * theta_z[ii][kk-1] - theta_z[ii][kk] - theta_z[ii][kk-2] ~ normal(0, 1 / smooth);
          else if (kk == dropbin)
            2 * theta_z[ii][kk-1] - theta_z[ii][kk-2] ~ normal(0, 1 / smooth);
          else if (kk == dropbin + 1)
            - theta_z[ii][kk-1] - theta_z[ii][kk-2] ~ normal(0, 1 / smooth);
          else if (kk == dropbin + 2)
            2 * theta_z[ii][kk-2] - theta_z[ii][kk-1] ~ normal(0, 1 / smooth);
          else
            2 * theta_z[ii][kk-2] - theta_z[ii][kk-1] - theta_z[ii][kk-3] ~ normal(0, 1 / smooth);
        }
    }

    // observed betas drawn from true parameters
    for (ii in 1:N) {
      //theta_z[ii] ~ normal(0, 1);
      theta_z[ii] ~ student_t(10, 0, 1);
      // implies: beta[ii] ~ multi_normal_cholesky(theta[ii], CholL[ii]);
    }
    // true parameters produced by linear expression
    for (kk in 1:K) {
      increment_log_prob(normal_log(transtheta[kk], x[kk] * gamma[kk], tau[kk]));
    }
}"

stan.model.fe <- "
data {
    int<lower=1> N; // number of study regions
    int<lower=1> M; // number of super-regions
    int<lower=1> K; // number of coefficients (not including dropped)
    int<lower=1> L; // number of predictors, including intercept

    vector[K] beta[N]; // estimated effects
    cov_matrix[K] Sigma[N]; // VCV across betas

    int<lower=1, upper=M> supers[N]; // which super each study is in
    matrix[N, L] x[K]; // predictors across regions

    real<lower=0> smooth; // prior on second derivative
    int<lower=0> dropbin; // index of dropped bin

    real<lower=0> maxsigma; // upper limit on sigma
    real<lower=0> maxgamma; // limits on gamma
}
transformed data {
    // Optimization: only compute decomposition once
    matrix[K, K] CholL[N];
    for (ii in 1:N)
      CholL[ii] <- cholesky_decompose(Sigma[ii]);
}
parameters {
    vector<lower=-maxgamma, upper=maxgamma>[M] fes[K];
    vector<lower=-maxgamma, upper=maxgamma>[L] gamma[K]; // surface parameters
    real<lower=0, upper=maxsigma> tau[K]; // variance in hyper equation
    vector[K] theta_z[N]; // z-scores of true effects
}
transformed parameters {
    vector[K] theta[N]; // true effects
    vector[N] transtheta[K]; // transpose of theta
    vector[N] allfes[K]; // including the right FEs for each obs.
    for (ii in 1:N) {
      theta[ii] <- beta[ii] + CholL[ii] * theta_z[ii];
      for (kk in 1:K) {
        transtheta[kk][ii] <- theta[ii][kk];
        allfes[kk][ii] <- fes[kk][supers[ii]];
      }
    }
}
model {
    // Add on the priors
    if (smooth > 0) {
      for (ii in 1:N)
        for (kk in 3:(K+1)) {
          if (kk < dropbin)
            2 * theta_z[ii][kk-1] - theta_z[ii][kk] - theta_z[ii][kk-2] ~ normal(0, 1 / smooth);
          else if (kk == dropbin)
            2 * theta_z[ii][kk-1] - theta_z[ii][kk-2] ~ normal(0, 1 / smooth);
          else if (kk == dropbin + 1)
            - theta_z[ii][kk-1] - theta_z[ii][kk-2] ~ normal(0, 1 / smooth);
          else if (kk == dropbin + 2)
            2 * theta_z[ii][kk-2] - theta_z[ii][kk-1] ~ normal(0, 1 / smooth);
          else
            2 * theta_z[ii][kk-2] - theta_z[ii][kk-1] - theta_z[ii][kk-3] ~ normal(0, 1 / smooth);
        }
    }

    // observed betas drawn from true parameters
    for (ii in 1:N) {
      theta_z[ii] ~ normal(0, 1);
      // implies: beta[ii] ~ multi_normal_cholesky(theta[ii], CholL[ii]);
    }
    // true parameters produced by linear expression
    for (kk in 1:K) {
      increment_log_prob(normal_log(transtheta[kk], allfes[kk] + x[kk] * gamma[kk], tau[kk]));
    }
}"

BayeserObservations <- setClass(
    "BayeserObservations",
    ## Define slots
    representation(K = "numeric",
                   L = "numeric",
                   allbetas = "matrix",
                   allvcv = "list",
                   allpredses = "list"))

setMethod("initialize", "BayeserObservations",
          function(.Object, K=11, L=4) {
              .Object@K <- K
              .Object@L <- L
              .Object@allbetas <- matrix(0, 0, K)
              .Object@allvcv <- list()
              .Object@allpredses <- list(matrix(0, 0, L), matrix(0, 0, L), matrix(0, 0, L),
                                     matrix(0, 0, L), matrix(0, 0, L), matrix(0, 0, L),
                                     matrix(0, 0, L), matrix(0, 0, L), matrix(0, 0, L),
                                     matrix(0, 0, L), matrix(0, 0, L))

              .Object
          })

## Add a new observation
setGeneric("addObs",
           def = function(this, betas, vcv, predses) {
               standardGeneric("addObs")
           })

setMethod("addObs",
          signature = "BayeserObservations",
          definition = function(this, betas, vcv, predses) {
              this@allbetas <- rbind(this@allbetas, as.matrix(betas))
              print(nrow(this@allbetas))
              this@allvcv[[length(this@allvcv)+1]] <- vcv

              for (kk in 1:nrow(predses))
                  this@allpredses[[kk]] <- rbind(this@allpredses[[kk]], predses[kk, ])

              this
          })

## Collect Stan Data
setGeneric("standata",
           def = function(this, smooth=0, dropbin=9, supers=NULL, fit=NULL) {
               standardGeneric("standata")
           })

setMethod("standata",
          signature = "BayeserObservations",
          definition = function(this, smooth=0, dropbin=9, supers=NULL, fit=NULL) {
              N <- length(this@allvcv)

              allpreds2 <- array(0, c(this@K, N, 4))
              for (jj in 1:this@K)
                  allpreds2[jj, , ] <- as.matrix(this@allpredses[[jj]])

              allvcv2 <- array(0, c(N, this@K, this@K))
              for (ii in 1:N)
                  allvcv2[ii, , ] <- as.matrix(this@allvcv[[ii]])

              for (ii in 1:N)
                  for (jj in 1:this@K)
                      if (allvcv2[ii, jj, jj] == 0)
                          allvcv2[ii, jj, jj] <- 1

              this@allbetas[is.na(this@allbetas)] <- 0

              result <- list(N=N, K=this@K, L=this@L, beta=this@allbetas, Sigma=allvcv2, x=allpreds2, smooth=smooth, dropbin=dropbin, maxsigma=max(colSds(as.matrix(this@allbetas))), maxgamma=max(colMeans(abs(this@allbetas))))

              if (!is.null(supers))
                  result[["supers"]] <- supers
          })

## Estimate the system
setGeneric("estimate",
           def = function(this, smooth=0, dropbin=9, supers=NULL, fit=NULL) {
               standardGeneric("estimate")
           })

setMethod("estimate",
          signature = "BayeserObservations",
          definition = function(this, smooth=0, dropbin=9, supers=NULL, fit=NULL) {
              stan.data <- standata(this, smooth=smooth, dropbin=dropbin, supers=supers, fit=fit)

              if (is.null(fit)) {
                  if (is.null(supers))
                      fit <- stan(model_code=stan.model, data=stan.data,
                                  iter = 1000, chains = 4)
                  else
                      fit <- stan(model_code=stan.model.fe, data=stan.data,
                                  iter = 1000, chains = 4)
              } else
                  fit <- stan(fit=fit, data=stan.data,
                              iter = 1000, chains = 4)

              fit
          })
