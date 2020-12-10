#!/bin/bash
source ${AGPROJ}/utils/projection_variables.sh

for crop in soy; do

	dir=${medians[${crop}]}
	base=${bases[${crop}]}
	vars=${variables[${crop}]}
	
	python -m generate.apply_aggregate \
	/shares/gcp/outputs/agriculture/impacts-mealy/${dir} \
	/mnt/CIL_agriculture/4_outputs/3_projections/6_value_checks/missing_aggregated_${dir}.csv \
	constcsv/estimation/agriculture/Data/1_raw/3_cropped_area/agglomerated-world-new-hierid-crop-weights.csv:hierid:${crop} \
	$vars  \
	$base

done