library(RJSONIO)
library(RCurl)

sources <- data.frame(ids=c('5706a749434fd7742c93b1ea', '5706a75b434fd775550740ad', '5706a76a434fd77676fac84b', '5706a780434fd7775beff0d8', '5706a790434fd77888f92d92', '5706ae0d434fd77cc7748df7'), regions=c('Brazil', 'Mexico', 'China', 'India', 'France', 'USA'))

## Collect all CVCs
for (ii in 1:nrow(sources)) {
    url <- paste0("http://dmas.berkeley.edu/model/get_beta_and_vcv?id=", sources$ids[ii], "&permission_override=true")
    raw_data <- getURL(url)
    ## Then covert from JSON into a list in R
    data <- fromJSON(raw_data)

    print(data)
}
