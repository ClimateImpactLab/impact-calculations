library(ggplot2)
args = commandArgs(trailingOnly=TRUE)

df <- read.csv(args[1])

gg <- ggplot_build(ggplot(df, aes(x=year)) +
        stat_smooth(aes(y=q17, colour='min'), se=F, span=.1) +
        stat_smooth(aes(y=q83, colour='max'), se=F, span=.1))
df.sm <- data.frame(year=gg$data[[1]]$x, ymin=gg$data[[1]]$y, ymax=gg$data[[2]]$y)

pdf("result.pdf", width=6, height=4)
ggplot(df) + geom_smooth(aes(x=year, y=q50 * 1e5), se=F, span=.1) +
    geom_ribbon(data=df.sm, aes(year, ymin=ymin * 1e5, ymax=ymax * 1e5), alpha=.5) +
    geom_hline(yintercept=0, size=.3) + scale_x_continuous(expand=c(0, 0), limits=c(2005, 2099)) +
    xlab("") + ylab("Heat and cold deaths per 100,000 per year") +
    ##scale_alpha_manual(name="", values=.5) +
    theme_bw() + theme(legend.justification=c(0,1), legend.position=c(0,1))
dev.off()
