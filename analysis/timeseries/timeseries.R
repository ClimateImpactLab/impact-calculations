timedatadir <- "timedata"

do.set <- 'ind'

if (do.set == 'global') {
    regionname <- "Entire globe"
    region <- "global"
    infix <- "-aggregated"
} else if (do.set == 'usa') {
    regionname <- "United States"
    region <- "USA"
    infix <- "-aggregated"
} else if (do.set == 'ind') {
    regionname <- "India"
    region <- "IND"
    infix <- "-aggregated"
}

full <- read.csv(paste0(timedatadir, "/rcp85-SSP3-", region, "-interpolated_mortality_all_ages", infix, "-diff.csv"))
dumb <- read.csv(paste0(timedatadir, "/rcp85-SSP3-", region, "-interpolated_mortality_dumb_all_ages", infix, "-diff.csv"))
coma <- read.csv(paste0(timedatadir, "/rcp85-SSP3-", region, "-interpolated_mortality_comatose_all_ages", infix, "-diff.csv"))
colb <- read.csv(paste0(timedatadir, "/rcp85-SSP3-", region, "-interpolated_mortality_all_ages-costs-aggregated-costs_lb-nodi.csv"))
coub <- read.csv(paste0(timedatadir, "/rcp85-SSP3-", region, "-interpolated_mortality_all_ages-costs-aggregated-costs_ub-nodi.csv"))

full$median <- full$median * 100000
dumb$median <- dumb$median * 100000
coma$median <- coma$median * 100000

colb$median <- colb$median - colb$median[colb$year == 2015]
colb$median[colb$year < 2015] <- 0

coub$median <- coub$median - coub$median[coub$year == 2015]
coub$median[coub$year < 2015] <- 0

fullcolb <- full
fullcolb$median <- fullcolb$median + c(0, colb$median)

fullcoub <- full
fullcoub$median <- fullcoub$median + c(0, coub$median)

full$model <- "Adapted mortality"
dumb$model <- "Adjusted for income + urban effects"
coma$model <- "No adaptation"
midcosts <- data.frame(model="Adapted mortality + adaptation cost", year=fullcoub$year, median=(fullcolb$median + fullcoub$median) / 2)

data1 <- rbind(full, dumb, coma, midcosts)
data2 <- data.frame(model="Upper and lower cost bounds", year=fullcolb$year, ymin=fullcolb$median, ymax=fullcoub$median)

library(ggplot2)

ggplot(data1) + geom_smooth(aes(x=year, y=median, colour=model), se=F, span=.1) +
    geom_ribbon(data=data2, aes(x=year, ymin=ymin, ymax=ymax, alpha="Upper and lower cost bounds")) +
    geom_hline(yintercept=0, size=.3) + scale_x_continuous(expand=c(0, 0), limits=c(2005, 2099)) +
    xlab("") + ylab("Heat and cold deaths per 100,000 per year") +
    scale_colour_manual(name="Model assumptions:", breaks=c("No adaptation", "Adjusted for income + urban effects", "Adapted mortality", "Adapted mortality + adaptation cost"), values=c("No adaptation"="#D55E00", "Adjusted for income + urban effects"="#E69F00", "Adapted mortality"="#009E73", "Adapted mortality + adaptation cost"="#000000")) +
    scale_alpha_manual(name="", values=.5) +
    ggtitle(paste("Comparison of mortality impacts by assumption, ", regionname)) +
    theme_bw() + theme(legend.justification=c(0,1), legend.position=c(0,1))

