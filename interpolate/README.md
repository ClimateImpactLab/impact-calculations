## Bayesian interpolation surface

* `surface.R` defines a class for performing the estimation
* `mortality.R` is a full estimation for mortality
* `display.R` shows a comparison of the Bayesian method against others

See the [Bayesian testing](https://docs.google.com/document/d/1g_3ukCzndYphH5OKTe-WO7ApeTW8FvwinJ_oVU2cFq4/edit?usp=sharing) document for more information.

## Basic usage

Create an object of type `SurfaceObservations`:
```
source("surface.R")
surface <- SurfaceObservations()
```

Add each region's values for beta (K values), its VCV (using a diagonal of the SE, squared, if not avaiable) (K x K), and a matrix of predictors (K x L):
```
surface <- addObs(surface, betas, vcv, predses)
```

Fit the model, by calling `surface`:
```
fit <- estimate.semur(surface)
```
or
```
fit <- estimate.bayes(surface)
```

If you use `estimate.semur`, you will get a result of type
`systemfit`, containing `coefficients` and `coefCov`.

If you use `estimate.bayes`, start by printing `fit`.  You'll see the
quantiles of estimated variable.  The most important values are in
`gamma`, the slopes of the surface.  Make sure that you have a decent
number of effective posterior draws in the printed `n_eff` column (500
- 2000), and that `Rhat` is near 1.

To use the values in `fit`, call `extract`:
```
la <- extract(fit, permute=T)
```

This returns the posterior draws, which empirically define the
distribution of each variable.  Specifically, `la$gamma` is a 4000 x K
x L matrix, where 4000 is the number of draws, K is the number of
bins, and L is the number of predictors.

You can write out either fitted surface by calling,
```
surface.write(surface, fit, "<FILENAME>.csvv", "<Short Description>", "<Version Prefix>", c(<DEPENDENCIES>), c(<STAGE 1 COEFFS>), c(<STAGE 2 PREDICTORS>))
```

And you can output the result to LaTeX:
```
as.latex(surface, fit)
```

## Loading data from DMAS

Start by installing `googlesheets` in R and getting an OAuth token:

```
install.packages("googlesheets")
library(googlesheets)
token <- gs_auth(cache = FALSE)
saveRDS(token, file="googlesheets_token.rds")
```