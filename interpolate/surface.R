library(methods)
library(matrixStats)
library(rstan)
library(systemfit)
library(yaml)

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
}
transformed data {
    // Optimization: only compute decomposition once
    matrix[K, K] CholL[N];
    for (ii in 1:N)
      CholL[ii] <- cholesky_decompose(Sigma[ii]);
}
parameters {
    vector[L] gamma[K]; // surface parameters
    real<lower=0> tau[K]; // variance in hyper equation
    vector[K] theta[N]; // z-scores of true effects
}
transformed parameters {
    vector[N] transtheta[K]; // transpose of theta
    for (ii in 1:N) {
      for (kk in 1:K)
        transtheta[kk][ii] <- theta[ii][kk];
    }
}
model {
    // Add on the priors
    if (smooth > 0) {
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
    }

    // observed betas drawn from true parameters
    for (ii in 1:N)
       beta[ii] ~ multi_normal_cholesky(theta[ii], CholL[ii]);

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
}
transformed data {
    // Optimization: only compute decomposition once
    matrix[K, K] CholL[N];
    for (ii in 1:N)
      CholL[ii] <- cholesky_decompose(Sigma[ii]);
}
parameters {
    vector[M] fes[K];
    vector[L] gamma[K]; // surface parameters
    real<lower=0> tau[K]; // variance in hyper equation
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

SurfaceObservations <- setClass(
    "SurfaceObservations",
    ## Define slots
    representation(K = "numeric",
                   L = "numeric",
                   allbetas = "matrix",
                   allvcv = "list",
                   allpredses = "list"))

setMethod("initialize", "SurfaceObservations",
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
          signature = "SurfaceObservations",
          definition = function(this, betas, vcv, predses) {
              ## Check that vcv is positive definite
              checkvcv <- as.matrix(vcv)
              eigenvalues <- eigen(checkvcv[rowSums(!is.finite(checkvcv)) == 0, colSums(!is.finite(checkvcv)) == 0])$values
              if (any(is.complex(eigenvalues)) || any(eigenvalues[eigenvalues != 0] < 0))
                  stop("The VCV is not symmetric or not positive definite.")

              this@allbetas <- rbind(this@allbetas, as.matrix(betas))
              this@allvcv[[length(this@allvcv)+1]] <- vcv

              for (kk in 1:nrow(predses))
                  this@allpredses[[kk]] <- rbind(this@allpredses[[kk]], predses[kk, ])

              this
          })

## Collect Stan Data
setGeneric("prepdata",
           def = function(this, smooth=0, dropbin=9) {
               standardGeneric("prepdata")
           })

setMethod("prepdata",
          signature = "SurfaceObservations",
          definition = function(this, smooth=0, dropbin=9) {
              N <- length(this@allvcv)

              allpreds2 <- array(0, c(this@K, N, this@L))
              for (jj in 1:this@K)
                  allpreds2[jj, , ] <- as.matrix(this@allpredses[[jj]])

              allvcv2 <- array(0, c(N, this@K, this@K))
              for (ii in 1:N)
                  allvcv2[ii, , ] <- as.matrix(this@allvcv[[ii]])

              for (ii in 1:N)
                  for (jj in 1:this@K)
                      if (allvcv2[ii, jj, jj] == 0)
                          allvcv2[ii, jj, jj] <- Inf

              this@allbetas[is.na(this@allbetas)] <- 0

              list(N=N, K=this@K, L=this@L, beta=this@allbetas, Sigma=allvcv2, x=allpreds2, smooth=smooth, dropbin=dropbin, maxsigma=max(colSds(as.matrix(this@allbetas))), maxgamma=max(colMeans(abs(this@allbetas))))
          })

## Estimate the system using Stan
setGeneric("estimate.bayes",
           def = function(this, smooth=0, dropbin=9, supers=NULL, fit=NULL, chains=4) {
               standardGeneric("estimate.bayes")
           })

setMethod("estimate.bayes",
          signature = "SurfaceObservations",
          definition = function(this, smooth=0, dropbin=9, supers=NULL, fit=NULL, chains=4) {
              stan.data <- prepdata(this, smooth=smooth, dropbin=dropbin)

              if (!is.null(supers)) {
                  stan.data[["supers"]] <- supers
                  stan.data[["M"]] <- max(supers)
              }

              if (is.null(fit)) {
                  if (is.null(supers))
                      fit <- stan(model_code=stan.model, data=stan.data,
                                  iter = 1000, chains = chains)
                  else
                      fit <- stan(model_code=stan.model.fe, data=stan.data,
                                  iter = 1000, chains = chains)
              } else
                  fit <- stan(fit=fit, data=stan.data,
                              iter = 1000, chains = chains)

              fit
          })

## Estimate the system using SUR
setGeneric("estimate.semur",
           def = function(this) {
               standardGeneric("estimate.semur")
           })

setMethod("estimate.semur",
          signature = "SurfaceObservations",
          definition = function(this) {
              data <- prepdata(this, smooth=0, dropbin=NA)

              regs <- list()
              sur.data <- data.frame(beta=c())
              sur.names <- c()

              for (ii in 1:data$K) {
                  new.names <- paste("pred", ii, 1:data$L, sep=".")
                  regs[[ii]] <- as.formula(paste("beta ~ 0 +", paste(new.names, collapse=" + ")))
                  if (nrow(sur.data) > 0) {
                      for (jj in 1:data$L)
                          sur.data[,new.names[jj]] <- 0
                  }

                  new.data <- cbind(data$beta[,ii], matrix(0, nrow=data$N, ncol=length(sur.names)), data$x[ii,,])
                  for (jj in 1:nrow(new.data)) {
                      serr <- sqrt(data$Sigma[jj, ii, ii])
                      if (serr == 0 || serr == Inf || (serr == 1 && new.data[jj, 1] == 0))
                          new.data[jj,] <- 0
                      else
                          new.data[jj,] <- new.data[jj,] / serr
                  }
                  sur.names <- c(sur.names, new.names)
                  colnames(new.data) <- c('beta', sur.names)
                  sur.data <- rbind(sur.data, new.data)
              }

              systemfit(regs, data=sur.data, method="OLS")
          })

## Standard output
setGeneric("surface.write",
           def = function(this, fit, filepath, oneline, version.prefix, dependencies) {
               standardGeneric("surface.write")
           })

setMethod("surface.write",
          signature = "SurfaceObservations",
          definition = function(this, fit, filepath, oneline, version.prefix, dependencies) {
              if (class(fit) == "systemfit") {
                  gammas <- as.numeric(fit$coefficients)
                  gammavcv <- as.matrix(fit$coefCov)
                  residvcv <- as.matrix(fit$residCov)
              } else {
                  la <- extract(fit, permute=T)
                  gammas <- as.numeric(t(colMeans(la$gamma)))
                  gammavcv <- matrix(NA, this@K * this@L, this@K * this@L)
                  for (kk1 in 1:this@K)
                      for (ll1 in 1:this@L)
                          for (kk2 in 1:this@K)
                              for (ll2 in 1:this@L) {
                                  rr <- (kk1 - 1) * this@L + ll1
                                  cc <- (kk2 - 1) * this@L + ll2
                                  if (is.na(gammavcv[rr, cc])) {
                                      klv <- cov(la$gamma[, kk1, ll1], la$gamma[, kk2, ll2])
                                      gammavcv[rr, cc] <- klv
                                      gammavcv[cc, rr] <- klv
                                  }
                              }
                  ## beta = mu + N(0, sigma + tau)
                  ## Assume Cov(sigma_i, sigma_j) = 0, Cov(sigma, tau) = 0
                  residvcv <- diag(colMeans(la$tau)^2)
              }

              ## Write out our special stage 2 format
              version <- paste0(version.prefix, '.', format(Sys.Date(), format="%Y%m%d"))

              fp <- file(filepath, 'w') # open the output
              cat("---\n", file=fp)
              cat(as.yaml(list(oneline=oneline, version=version,
                               dependencies=paste(dependencies, collapse=", "),
                               description="Generated by surface.R; contains stage 2 fit.",
                               variables=list(NN="Contributing observations [int]",
                                              L="Stage 2 predictors [int]",
                                              K="Stage 1 coefficients [int]",
                                              gamma="Stage 2 coefficients, by L then K [float LK]",
                                              gammavcv="Stage 2 VCV [float LKxLK]",
                                              residvcv="Stage 2 residual VCV [float KxK]"))),
                  file=fp)
              cat("...\n", file=fp)
              cat("NN,", length(this@allvcv), "\n", file=fp)
              cat("L,", this@L, "\n", file=fp)
              cat("K,", this@K, "\n", file=fp)
              cat("gamma\n", file=fp)
              write.table(t(gammas), fp, sep=',', row.names=F, col.names=F)
              cat("gammavcv\n", file=fp)
              write.table(gammavcv, fp, sep=',', row.names=F, col.names=F)
              cat("residvcv\n", file=fp)
              write.table(residvcv, fp, sep=',', row.names=F, col.names=F)
              close(fp)
          })
