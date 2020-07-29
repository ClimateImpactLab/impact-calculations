#!/bin/bash

climates_models=()
i=0
prefix="/shares/gcp/outputs/temps/rcp45/"
for f in /shares/gcp/outputs/temps/rcp45/*; do 
	climate_models[$i]=${f#"$prefix"}
	i=$((i+1))
done 

for climate_model in "${climate_models[@]}"
do 
	for rcp in "rcp45" "rcp85"
	do 
		printf 'running:%s\n' " $1 $climate_model $rcp"
		python -m generate.seasonal_climategen $1 $climate_model $rcp $2 &
	done
done