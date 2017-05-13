## mom1s - mom4s are several instances of the first four moments of the distribution
## Assume that mu changes, but var remains the same
estimate.var <- function(mom1s, mom2s, mom3s, mom4s) {
    ## mom1 = mu
    ## mom2 = mu^2 + var
    ## mom3 = 3 mu var + mu^3
    ## mom4 = 3 var^2 + 6 mu^2 var + mu^4
    mus <- mom1s
    var1s <- mom2s - mus^2

    yy <- c(mom2s - mus^2, mom3s - mus^3, mom4s - mus^4)
    bb <- c(rep(1, length(mus)), 3 * mus, 3 * var1s + 6 * mus^2)

    var2 = lm(yy ~ 0 + bb)$coeff

    bb <- c(rep(1, length(mus)), 3 * mus, 3 * var2 + 6 * mus^2)
    lm(yy ~ 0 + bb)$coeff
}

## Calculate for all regions simultaneously
estimate.var.vector <- function(mom1ss, mom2ss, mom3ss) {
    ## mom1 = mu
    ## mom2 = mu^2 + var
    ## mom3 = 3 mu var + mu^3
    muss <- mom1ss
    var1s <- rowMeans(mom2ss - muss^2)
    var2s <- rowMeans((mom3ss - muss^3) / (3 * muss))
    var2s[var2s < 0] <- var1s[var2s < 0] # don't allow negatives

    ((sqrt(var1s) + sqrt(var2s)) / 2)^2
}

## Calculate the 5th moment of the distribution
## vars can either be length 1 (from estimate.var) or the same dimension as mus
normal.power5 <- function(mus, vars) {
    15 * vars^2 * mus + 10 * vars * mus^3 + mus^5
}
