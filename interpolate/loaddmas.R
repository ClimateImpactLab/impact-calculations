## Functions for loading estimates from DMAS
## See the README file for installatino and OAuth instructions.

library(googlesheets)
suppressMessages(library(dplyr))

gs_auth(token="googlesheets_token.rds")

dmasinfo <- gs_title("Master DMAS Information")
models <- dmasinfo %>% gs_read(ws="Models")

get.dmasid <- function(gcpid) {
    models %>% filter(`Unique ID` == gcpid) %>%
        select(`DMAS ID`)
}
