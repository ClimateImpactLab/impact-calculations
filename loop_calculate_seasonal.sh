#!/bin/bash

#nohup ./calculate_seasonal.sh "maize_seasonaltasmax.nc4"
#wait 
#./calculate_seasonal.sh "maize_seasonaltasmax.nc4"

#"maize_seasonalpr.nc4" "maize_seasonaledd.nc4" "maize_monthbinpr.nc4"


./calculate_seasonal.sh "rice_seasonaltasmax.nc4" "rice"
wait
./calculate_seasonal.sh "soy_seasonaltasmax.nc4" "soy"
wait 
./calculate_seasonal.sh "rice_seasonalpr.nc4" "rice"
wait
./calculate_seasonal.sh "soy_seasonalpr.nc4" "soy"


