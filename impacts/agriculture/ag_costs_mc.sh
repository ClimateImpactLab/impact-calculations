#!/bin/bash

## IDEAS TO PARALLELIZE (SEE THE N-BATCH OPTION, may need to divide evenly...)
## https://unix.stackexchange.com/questions/103920/parallelize-a-bash-for-loop


N=15 # Number of processors to use


## USER: set the base directory by uncommenting the line associated with the crop you want to run.

# base='/shares/gcp/outputs/agriculture/impacts-mealy/montecarlo-corn-140521/montecarlo/'
# base='/shares/gcp/outputs/agriculture/impacts-mealy/montecarlo-soy-140521/montecarlo/'
# base='/shares/gcp/outputs/agriculture/impacts-mealy/montecarlo-rice-140521/montecarlo/'
# base='/shares/gcp/outputs/agriculture/impacts-mealy/montecarlo-cassava-140521/montecarlo/'
base='/shares/gcp/outputs/agriculture/impacts-mealy/montecarlo-sorghum-140521/montecarlo/'
# base='/shares/gcp/outputs/agriculture/impacts-mealy/montecarlo-wheat_spring-300421/montecarlo/'
# base='/shares/gcp/outputs/agriculture/impacts-mealy/montecarlo-wheat_winter-300421/montecarlo/'



for m in 'ACCESS1-0' 'bcc-csm1-1' 'BNU-ESM' 'CanESM2' 'CCSM4' 'CESM1-BGC' 'CNRM-CM5' 'CSIRO-Mk3-6-0' 'GFDL-CM3' 'GFDL-ESM2G' 'GFDL-ESM2M' 'IPSL-CM5A-LR' 'IPSL-CM5A-MR' 'MIROC-ESM-CHEM' 'MIROC-ESM' 'MIROC5' 'MPI-ESM-LR' 'MPI-ESM-MR' 'MRI-CGCM3' 'inmcm4' 'NorESM1-M' 'surrogate_MRI-CGCM3_01' 'surrogate_GFDL-ESM2G_01' 'surrogate_MRI-CGCM3_06' 'surrogate_GFDL-ESM2G_06' 'surrogate_MRI-CGCM3_11' 'surrogate_GFDL-ESM2G_11' 'surrogate_GFDL-CM3_89' 'surrogate_CanESM2_89' 'surrogate_GFDL-CM3_89' 'surrogate_GFDL-CM3_94' 'surrogate_CanESM2_94' 'surrogate_GFDL-CM3_99' 'surrogate_CanESM2_99'
# for m in 'bcc-csm1-1' # For testing
do

  for r in 45 85
  do

    for s in 3 # 1 2 3 4 5
    do

      # SSP1/RCP85 and SSP5/RCP45 are not compatible projections and are not run. ACCESS1-0 RCP8.5 is dropped.
      if [ $s = 1 ] && [ $r = 85 ]; then
	continue
      elif [ $s = 5 ] && [ $r = 45 ]; then
	continue
      elif [ $m = 'ACCESS1-0' ] && [ $r = 85 ]; then
        continue
      elif [ $m = 'surrogate_GFDL-ESM2G_06' ] && [ $r = 45 ]; then
        continue
      fi

      
      for i in 'low' 'high'
      do

	(
	for b in 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 # 2 6  ,  0 1 3 4 5 7 8 9 10
	do
	  
	  # Parallelization, following this: https://unix.stackexchange.com/questions/103920/parallelize-a-bash-for-loop
	  ((j=j%N)); ((j++==0)) && wait


          # Extract the seed value for the vcv draw from the .yaml file
          seed="$(grep -oP '(?<=seed-csvv: )[0-9]+' $base/batch$b/rcp$r/$m/$i/SSP$s/pvals.yml)"

          # Make sure we extracted a number
          if ! [[ $seed =~ ^[0-9]+$ ]] ; then
            echo "Error: The seed value is not a number. Check pvals.yml for batch$b rcp$r ssp$s iam$i model$m" >&2; exit 1 
          fi

	  echo "Batch $b"

          
	  # Set for arguments, with a 13 year averaging period for the income covariate.

          # Rscript tmp_and_prcp_costs.R "$base/batch$b" 'maize' $m $r $s $i 13 $seed &
	  # Rscript tmp_and_prcp_costs.R "$base/batch$b" 'soy' $m $r $s $i 13 $seed &
	  # Rscript tmp_and_prcp_costs.R "$base/batch$b" 'rice' $m $r $s $i 13 $seed &
	  # Rscript tmp_and_prcp_costs.R "$base/batch$b" 'cassava' $m $r $s $i 13 $seed &
	  Rscript tmp_and_prcp_costs.R "$base/batch$b" 'sorghum' $m $r $s $i 13 $seed &	
	  # Rscript tmp_and_prcp_costs.R "$base/batch$b" 'wheat-spring' $m $r $s $i 13 $seed &
	  # Rscript tmp_and_prcp_costs.R "$base/batch$b" 'wheat-winter' $m $r $s $i 13 $seed &
	  


        done
	wait
	)
      done
    done
  done
done

chgrp -R gcp $base
chmod -R 775 $base

