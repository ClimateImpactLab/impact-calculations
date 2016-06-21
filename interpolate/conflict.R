setwd("~/Repos/impact-calculations/interpolate")

source("bayeser.R")

basedir <- "~/Dropbox/ChicagoRAs_Reanalysis/conflict_sharing/Theo"
setwd(basedir)

##### TEMP #####

### Interpersonal - author preferred

# Specification of 1st Stage model
K <- 1
spec <- "temp_auth_bsw"

# Specification of 2nd Stage model
L <- 4
include.2stgfe <- FALSE

## Create a BayesObservations object to hold the data
bayeser <- BayeserObservations(K=K, L=L)
## Read inputs
climvars <- "effect_1sd"
inputs <- read.csv("inputs/temp_0_2_auth_bsw.csv")
inputs$loggdppc <- log(inputs$gdppc)
inputs$logpopop <- log(inputs$popop)
effects <- inputs[, climvars]
vcv <- inputs[, "se_1sd"]
predses <- cbind(data.frame(const=1), inputs[, c('ta', 'logpopop', 'loggdppc')])
names(predses) <- c('const', 'atemp', 'popop', 'gdppc')

for (jj in 1:nrow(inputs)) {
  if (max(c(is.na(effects[jj]), is.na(vcv[jj]), is.na(predses[jj,])))==0) {
    bayeser <- addObs(bayeser, effects[jj], vcv[jj], predses[jj,])
  } else {
    print(jj)
  }
}

fit <- estimate(bayeser)
print(fit)
la <- extract(fit, permute=T)

## Output bin surface parameters
kk <- 1
result <- data.frame(method='fullba', climvar="atemp",
           intercept_coef=mean(la$gamma[, kk, 1]),
           atemp_coef=mean(la$gamma[, kk, 2]),
           popop_coef=mean(la$gamma[, kk, 3]),
           gdppc_coef=mean(la$gamma[, kk, 4]),
           intercept_serr=sd(la$gamma[, kk, 1]),
           atemp_serr=sd(la$gamma[, kk, 2]),
           popop_serr=sd(la$gamma[, kk, 3]),
           gdppc_serr=sd(la$gamma[, kk, 4]))

write.csv(result, paste0("outputs/conflict-personal_", spec, "_fullbayes.csv"), row.names=F)

### Interpersonal - combined

# Specification of 1st Stage model
K <- 1
spec <- "temp_comb_bsw"

# Specification of 2nd Stage model
L <- 4
include.2stgfe <- FALSE

## Create a BayesObservations object to hold the data
bayeser <- BayeserObservations(K=K, L=L)
## Read inputs
climvars <- "effect_1sd"
inputs <- read.csv("inputs/temp_0_2_comb_bsw.csv")
inputs$loggdppc <- log(inputs$gdppc)
inputs$logpopop <- log(inputs$popop)
effects <- inputs[, climvars]
vcv <- inputs[, "se_1sd"]
predses <- cbind(data.frame(const=1), inputs[, c('ta', 'logpopop', 'loggdppc')])
names(predses) <- c('const', 'atemp', 'popop', 'gdppc')

for (jj in 1:nrow(inputs)) {
  if (max(c(is.na(effects[jj]), is.na(vcv[jj]), is.na(predses[jj,])))==0) {
    bayeser <- addObs(bayeser, effects[jj], vcv[jj], predses[jj,])
  } else {
    print(jj)
  }
}

fit <- estimate(bayeser)
print(fit)
la <- extract(fit, permute=T)

## Output bin surface parameters
kk <- 1
result <- data.frame(method='fullba', climvar="atemp",
                     intercept_coef=mean(la$gamma[, kk, 1]),
                     atemp_coef=mean(la$gamma[, kk, 2]),
                     popop_coef=mean(la$gamma[, kk, 3]),
                     gdppc_coef=mean(la$gamma[, kk, 4]),
                     intercept_serr=sd(la$gamma[, kk, 1]),
                     atemp_serr=sd(la$gamma[, kk, 2]),
                     popop_serr=sd(la$gamma[, kk, 3]),
                     gdppc_serr=sd(la$gamma[, kk, 4]))

write.csv(result, paste0("outputs/conflict-personal_", spec, "_fullbayes.csv"), row.names=F)

### Intergroup - author preferred

# Specification of 1st Stage model
K <- 1
spec <- "temp_auth_bsw"

# Specification of 2nd Stage model
L <- 4
include.2stgfe <- FALSE

## Create a BayesObservations object to hold the data
bayeser <- BayeserObservations(K=K, L=L)
## Read inputs
climvars <- "effect_1sd"
inputs <- read.csv("inputs/temp_0_1_auth_bsw.csv")
inputs$loggdppc <- log(inputs$gdppc)
inputs$logpopop <- log(inputs$popop)
effects <- inputs[, climvars]
vcv <- inputs[, "se_1sd"]
predses <- cbind(data.frame(const=1), inputs[, c('ta', 'logpopop', 'loggdppc')])
names(predses) <- c('const', 'atemp', 'popop', 'gdppc')

for (jj in 1:nrow(inputs)) {
  if (max(c(is.na(effects[jj]), is.na(vcv[jj]), is.na(predses[jj,])))==0) {
    bayeser <- addObs(bayeser, effects[jj], vcv[jj], predses[jj,])
  } else {
    print(jj)
  }
}

fit <- estimate(bayeser)
print(fit)
la <- extract(fit, permute=T)

## Output bin surface parameters
kk <- 1
result <- data.frame(method='fullba', climvar="atemp",
                     intercept_coef=mean(la$gamma[, kk, 1]),
                     atemp_coef=mean(la$gamma[, kk, 2]),
                     popop_coef=mean(la$gamma[, kk, 3]),
                     gdppc_coef=mean(la$gamma[, kk, 4]),
                     intercept_serr=sd(la$gamma[, kk, 1]),
                     atemp_serr=sd(la$gamma[, kk, 2]),
                     popop_serr=sd(la$gamma[, kk, 3]),
                     gdppc_serr=sd(la$gamma[, kk, 4]))

write.csv(result, paste0("outputs/conflict-group_", spec, "_fullbayes.csv"), row.names=F)

### Intergroup - combined

# Specification of 1st Stage model
K <- 1
spec <- "temp_comb_bsw"

# Specification of 2nd Stage model
L <- 4
include.2stgfe <- FALSE

## Create a BayesObservations object to hold the data
bayeser <- BayeserObservations(K=K, L=L)
## Read inputs
climvars <- "effect_1sd"
inputs <- read.csv("inputs/temp_0_1_comb_bsw.csv")
inputs$loggdppc <- log(inputs$gdppc)
inputs$logpopop <- log(inputs$popop)
effects <- inputs[, climvars]
vcv <- inputs[, "se_1sd"]
predses <- cbind(data.frame(const=1), inputs[, c('ta', 'logpopop', 'loggdppc')])
names(predses) <- c('const', 'atemp', 'popop', 'gdppc')

for (jj in 1:nrow(inputs)) {
  if (max(c(is.na(effects[jj]), is.na(vcv[jj]), is.na(predses[jj,])))==0) {
    bayeser <- addObs(bayeser, effects[jj], vcv[jj], predses[jj,])
  } else {
    print(jj)
  }
}

fit <- estimate(bayeser)
print(fit)
la <- extract(fit, permute=T)

## Output bin surface parameters
kk <- 1
result <- data.frame(method='fullba', climvar="atemp",
                     intercept_coef=mean(la$gamma[, kk, 1]),
                     atemp_coef=mean(la$gamma[, kk, 2]),
                     popop_coef=mean(la$gamma[, kk, 3]),
                     gdppc_coef=mean(la$gamma[, kk, 4]),
                     intercept_serr=sd(la$gamma[, kk, 1]),
                     atemp_serr=sd(la$gamma[, kk, 2]),
                     popop_serr=sd(la$gamma[, kk, 3]),
                     gdppc_serr=sd(la$gamma[, kk, 4]))

write.csv(result, paste0("outputs/conflict-group_", spec, "_fullbayes.csv"), row.names=F)


##### TEMP + PRCP #####

### Interpersonal - author preferred

# Specification of 1st Stage model
K <- 1
spec <- "temp_auth_bsw"

# Specification of 2nd Stage model
L <- 5
include.2stgfe <- FALSE

## Create a BayesObservations object to hold the data
bayeser <- BayeserObservations(K=K, L=L)
## Read inputs
climvars <- "effect_1sd"
inputs <- read.csv("inputs/temp_0_2_auth_bsw.csv")
inputs$loggdppc <- log(inputs$gdppc)
inputs$logpopop <- log(inputs$popop)
effects <- inputs[, climvars]
vcv <- inputs[, "se_1sd"]
predses <- cbind(data.frame(const=1), inputs[, c('ta', 'precip', 'logpopop', 'loggdppc')])
names(predses) <- c('const', 'atemp', 'aprcp', 'popop', 'gdppc')

for (jj in 1:nrow(inputs)) {
  if (max(c(is.na(effects[jj]), is.na(vcv[jj]), is.na(predses[jj,])))==0) {
    bayeser <- addObs(bayeser, effects[jj], vcv[jj], predses[jj,])
  } else {
    print(jj)
  }
}

fit <- estimate(bayeser)
print(fit)
la <- extract(fit, permute=T)

## Output bin surface parameters
kk <- 1
result <- data.frame(method='fullba', climvar="atemp",
                     intercept_coef=mean(la$gamma[, kk, 1]),
                     atemp_coef=mean(la$gamma[, kk, 2]),
                     aprcp_coef=mean(la$gamma[, kk, 3]),
                     popop_coef=mean(la$gamma[, kk, 4]),
                     gdppc_coef=mean(la$gamma[, kk, 5]),
                     intercept_serr=sd(la$gamma[, kk, 1]),
                     atemp_serr=sd(la$gamma[, kk, 2]),
                     aprcp_serr=sd(la$gamma[, kk, 3]),
                     popop_serr=sd(la$gamma[, kk, 4]),
                     gdppc_serr=sd(la$gamma[, kk, 5]))

write.csv(result, paste0("outputs/conflict-personal_", spec, "_fullbayes.csv"), row.names=F)

### Interpersonal - combined

# Specification of 1st Stage model
K <- 1
spec <- "temp_comb_bsw"

# Specification of 2nd Stage model
L <- 5
include.2stgfe <- FALSE

## Create a BayesObservations object to hold the data
bayeser <- BayeserObservations(K=K, L=L)
## Read inputs
climvars <- "effect_1sd"
inputs <- read.csv("inputs/temp_0_2_comb_bsw.csv")
inputs$loggdppc <- log(inputs$gdppc)
inputs$logpopop <- log(inputs$popop)
effects <- inputs[, climvars]
vcv <- inputs[, "se_1sd"]
predses <- cbind(data.frame(const=1), inputs[, c('ta', 'precip', 'logpopop', 'loggdppc')])
names(predses) <- c('const', 'atemp', 'aprcp', 'popop', 'gdppc')

for (jj in 1:nrow(inputs)) {
  if (max(c(is.na(effects[jj]), is.na(vcv[jj]), is.na(predses[jj,])))==0) {
    bayeser <- addObs(bayeser, effects[jj], vcv[jj], predses[jj,])
  } else {
    print(jj)
  }
}

fit <- estimate(bayeser)
print(fit)
la <- extract(fit, permute=T)

## Output bin surface parameters
kk <- 1
result <- data.frame(method='fullba', climvar="atemp",
                     intercept_coef=mean(la$gamma[, kk, 1]),
                     atemp_coef=mean(la$gamma[, kk, 2]),
                     aprcp_coef=mean(la$gamma[, kk, 3]),
                     popop_coef=mean(la$gamma[, kk, 4]),
                     gdppc_coef=mean(la$gamma[, kk, 5]),
                     intercept_serr=sd(la$gamma[, kk, 1]),
                     atemp_serr=sd(la$gamma[, kk, 2]),
                     aprcp_serr=sd(la$gamma[, kk, 3]),
                     popop_serr=sd(la$gamma[, kk, 4]),
                     gdppc_serr=sd(la$gamma[, kk, 5]))

write.csv(result, paste0("outputs/conflict-personal_", spec, "_fullbayes.csv"), row.names=F)

### Intergroup - author preferred

# Specification of 1st Stage model
K <- 1
spec <- "temp_auth_bsw"

# Specification of 2nd Stage model
L <- 5
include.2stgfe <- FALSE

## Create a BayesObservations object to hold the data
bayeser <- BayeserObservations(K=K, L=L)
## Read inputs
climvars <- "effect_1sd"
inputs <- read.csv("inputs/temp_0_1_auth_bsw.csv")
inputs$loggdppc <- log(inputs$gdppc)
inputs$logpopop <- log(inputs$popop)
effects <- inputs[, climvars]
vcv <- inputs[, "se_1sd"]
predses <- cbind(data.frame(const=1), inputs[, c('ta', 'precip', 'logpopop', 'loggdppc')])
names(predses) <- c('const', 'atemp', 'aprcp', 'popop', 'gdppc')

for (jj in 1:nrow(inputs)) {
  if (max(c(is.na(effects[jj]), is.na(vcv[jj]), is.na(predses[jj,])))==0) {
    bayeser <- addObs(bayeser, effects[jj], vcv[jj], predses[jj,])
  } else {
    print(jj)
  }
}

fit <- estimate(bayeser)
print(fit)
la <- extract(fit, permute=T)

## Output bin surface parameters
kk <- 1
result <- data.frame(method='fullba', climvar="atemp",
                     intercept_coef=mean(la$gamma[, kk, 1]),
                     atemp_coef=mean(la$gamma[, kk, 2]),
                     aprcp_coef=mean(la$gamma[, kk, 3]),
                     popop_coef=mean(la$gamma[, kk, 4]),
                     gdppc_coef=mean(la$gamma[, kk, 5]),
                     intercept_serr=sd(la$gamma[, kk, 1]),
                     atemp_serr=sd(la$gamma[, kk, 2]),
                     aprcp_serr=sd(la$gamma[, kk, 3]),
                     popop_serr=sd(la$gamma[, kk, 4]),
                     gdppc_serr=sd(la$gamma[, kk, 5]))

write.csv(result, paste0("outputs/conflict-group_", spec, "_fullbayes.csv"), row.names=F)

### Intergroup - combined

# Specification of 1st Stage model
K <- 1
spec <- "temp_comb_bsw"

# Specification of 2nd Stage model
L <- 5
include.2stgfe <- FALSE

## Create a BayesObservations object to hold the data
bayeser <- BayeserObservations(K=K, L=L)
## Read inputs
climvars <- "effect_1sd"
inputs <- read.csv("inputs/temp_0_1_comb_bsw.csv")
inputs$loggdppc <- log(inputs$gdppc)
inputs$logpopop <- log(inputs$popop)
effects <- inputs[, climvars]
vcv <- inputs[, "se_1sd"]
predses <- cbind(data.frame(const=1), inputs[, c('ta', 'precip', 'logpopop', 'loggdppc')])
names(predses) <- c('const', 'atemp', 'aprcp', 'popop', 'gdppc')

for (jj in 1:nrow(inputs)) {
  if (max(c(is.na(effects[jj]), is.na(vcv[jj]), is.na(predses[jj,])))==0) {
    bayeser <- addObs(bayeser, effects[jj], vcv[jj], predses[jj,])
  } else {
    print(jj)
  }
}

fit <- estimate(bayeser)
print(fit)
la <- extract(fit, permute=T)

## Output bin surface parameters
kk <- 1
result <- data.frame(method='fullba', climvar="atemp",
                     intercept_coef=mean(la$gamma[, kk, 1]),
                     atemp_coef=mean(la$gamma[, kk, 2]),
                     aprcp_coef=mean(la$gamma[, kk, 3]),
                     popop_coef=mean(la$gamma[, kk, 4]),
                     gdppc_coef=mean(la$gamma[, kk, 5]),
                     intercept_serr=sd(la$gamma[, kk, 1]),
                     atemp_serr=sd(la$gamma[, kk, 2]),
                     aprcp_serr=sd(la$gamma[, kk, 3]),
                     popop_serr=sd(la$gamma[, kk, 4]),
                     gdppc_serr=sd(la$gamma[, kk, 5]))

write.csv(result, paste0("outputs/conflict-group_", spec, "_fullbayes.csv"), row.names=F)


