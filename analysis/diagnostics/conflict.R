## Checking gammas
obs <- read.csv("~/Dropbox/Global ACP/CONFLICT/results/stage1/interpersonal_violent_tp3.csv")
obs$avgT2 <- obs$avgT^2
obs$avgT3 <- obs$avgT^3
obs$avgprecip2 <- obs$avgprecip^2
obs$avgprecip3 <- obs$avgprecip^3
obs$loggdppc <- log(obs$gdppc)
obs$loggdppc2 <- log(obs$gdppc)^2
obs$loggdppc3 <- log(obs$gdppc)^3
obs$logpopop <- log(obs$popop)
obs$logpopop2 <- log(obs$popop)^2
obs$logpopop3 <- log(obs$popop)^3

mod <- lm(beta_temp ~ avgT + avgT2 + avgT3 + avgprecip + avgprecip2 + avgprecip3 + loggdppc + loggdppc2 + loggdppc3 + logpopop + logpopop2 + logpopop3, data=obs)
summary(mod)

## Checks out.

## Checking that projection can be gotten from beta

betas <- c(0.420368, 0.016001, -0.0001653, 3.15e-07)
beta.preds <- c(0, 524.7748, 524.7748^2, 524.7748^3)
sum(betas * beta.preds)

## 8.39?  <--- Is this because missing an intercept?

## Checking projections for observed regions
## personal_violent_tp3_cubic_semur_auto.csvv

## study_number,study_name,outcome_IDV,region,conflicttype,iso,model,beta_precip1,se_precip1,beta_precip2,se_precip2,beta_precip3,se_precip3,beta_temp,se_temp,lag,conflict_subtype,estimates_at_level,gdppc,popop,ag_gdp,population,avgT,varT,avgprecip,varP
## 17,Gonzalez et al 2014,homicide rate,Aguascalientes,2,MEX,contemp+lag,0.016001,0.0088985,-0.0001653,0.0000735,3.15E-07,1.24E-07,0.420368,0.1334588,comb,violent,adm1_level,13118.84,7495.752,,,17.00615,0.2016145,524.7748,110.9512

preds <- c(17.00615, 524.7748, log(c(13118.84,7495.752)))
allpreds <- c(1, preds, preds^2, preds^3)
gamma <- c(409.307759569419,2.55229358893961,-0.0728084880071852,-17.3816133550868,-108.85708447446,-0.414987406488656,4.08883780303312e-05,3.8351089543137,11.7493893750377,0.0110895485276968,-7.0015981675994e-09,-0.247961202038443,-0.412563824869194,-107.289684239237,-0.68957583344048,0.00539750162424575,2.4154235799336,34.9224051536951,0.0540799342505156,-3.08357538779761e-06,-0.54085148728436,-3.84074198838992,-0.0011721007789998,5.28485658341083e-10,0.0324970730709764,0.139725655632896,1.47950631641141,0.00757339933873887,-5.45671300031948e-05,-0.0207320425339594,-0.500080246911491,-0.000609121766381091,3.20637064549822e-08,0.00510518643632247,0.0563552194883136,1.33807700840089e-05,-5.64094260780739e-12,-0.0003226981535979,-0.00209808453195074,-0.00568075913702231,-2.26246092598158e-05,1.42578419200546e-07,5.7115598243254e-05,0.00195594352779719,1.90180621896782e-06,-8.56761882058386e-11,-1.51735044405205e-05,-0.000223120025084924,-4.25959087097385e-08,1.53842574672324e-14,9.93774931804145e-07,8.39910664520556e-06)

betas <- c(sum(allpreds * gamma[1:13]), sum(allpreds * gamma[14:26]), sum(allpreds * gamma[27:39]), sum(allpreds * gamma[40:52]))
## -1.0685752759 -0.0203621506 -0.0011592775  0.0000082302
## Expected: 0.420368, 0.016001, -0.0001653, 3.15E-07

beta.preds <- c(17.00615, 524.7748, 524.7748^2, 524.7748^3)
sum(betas * beta.preds)

######

## How does my distribution of betas compare?

allbetas <- read.csv("~/research/gcp/conflict/impacts-drywood/median/median/personal_violent_tp3_cubic_semur_auto-betas.csv")

library(ggplot2)

ggplot(obs, aes(y=beta_temp, x=study_name)) +
    geom_boxplot() + coord_flip() + scale_y_log10() + theme_bw()

ggplot(data.frame(beta=c(allbetas$beta.temp, obs$beta_temp), group=c(rep('predicted', nrow(allbetas)), rep('observed', nrow(obs)))), aes(x=beta, colour=group)) +
    geom_density()

hist(allbetas$beta.temp)
hist(obs$beta_temp)

## Also check property and intergroup

obs <- read.csv("~/Dropbox/Global ACP/CONFLICT/results/stage1/intergroup_tp3.csv")

ggplot(obs, aes(y=beta_temp, x=study_name)) +
    geom_boxplot() + coord_flip() + scale_y_log10() + theme_bw()

obs <- read.csv("~/Dropbox/Global ACP/CONFLICT/results/stage1/interpersonal_property_tavg.csv")

ggplot(obs, aes(y=beta_temp, x=study_name)) +
    geom_boxplot() + coord_flip() + scale_y_log10() + theme_bw()
