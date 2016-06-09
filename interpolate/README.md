## Bayesian interpolation surface

* `bayeser.R` defines a class for performing the estimation
* `mortality.R` is a full estimation for mortality
* `display.R` shows a comparison of the Bayesian method against others

See the [Bayesian testing](https://docs.google.com/document/d/1g_3ukCzndYphH5OKTe-WO7ApeTW8FvwinJ_oVU2cFq4/edit?usp=sharing) document for more information.

## Basic usage

Create an object of type `BayeserObservations`:
```
source("bayeser.R")
bayeser <- BayeserObservations()
```

Add each region's values for beta (K values), its VCV (using a diagonal of the SE, squared, if not avaiable) (K x K), and a matrix of predictors (K x L):
```
bayeser <- addObs(bayeser, betas, vcv, predses)
```

Fit the model, by calling `estimate`:
```
fit <- estimate(bayeser)
```

Now you can check it, by printing `fit`.  You'll see the quantiles of
estimated variable.  The most important values are in `gamma`, the
slopes of the surface.  Make sure that you have a decent number of
effective posterior draws in the printed `n_eff` column (500 - 2000),
and that `Rhat` is near 1.

To use the values in `fit`, call `extract`:
```
la <- extract(fit, permute=T)
```

This returns the posterior draws, which empirically define the
distribution of each variable.  Specifically, `la$gamma` is a 4000 x K
x L matrix, where 4000 is the number of draws, K is the number of
bins, and L is the number of predictors.
