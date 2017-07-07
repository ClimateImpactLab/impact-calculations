#!/bin/bash

### CHOOSE rates OR levels, edf OR values
runs=batch
spec=poly4
levrat=levels
vals=values
###

if [ $levrat == 'levels' ]
then
  suff=-levels
else
  suff=''
fi
if [ $spec == 'poly4' ]
then
  filespec=POLY-4
elif [ $spec == 'poly5' ]
then
  filespec=POLY-5
else
  filespec=CSpline-LS
fi

config_file=mortality_${spec}_${runs}
dirlog=~/sharing/mortality/damage_function/code/log
mkdir -p ${dirlog}/${runs}/${spec}
cd ~/sharing/mortality/damage_function/code/prospectus-tools/gcp/extract/
for age in young older oldest
do
  nohup python quantiles.py configs/${config_file}.yml --suffix=_${age} global_interaction_Tmean-${filespec}-AgeSpec-${age}${suff} > ${dirlog}/${runs}/${spec}/${levrat}_${vals}_${age}.txt 2>&1 &
  nohup python quantiles.py configs/${config_file}.yml --suffix=_${age}_histclim global_interaction_Tmean-${filespec}-AgeSpec-${age}-histclim${suff} > ${dirlog}/${runs}/${spec}/${levrat}_${vals}_${age}_histclim.txt 2>&1 &
  nohup python quantiles.py configs/${config_file}_costs_ub.yml --suffix=_${age}_costs_ub global_interaction_Tmean-${filespec}-AgeSpec-${age}-costs${suff} > ${dirlog}/${runs}/${spec}/${levrat}_${vals}_${age}_costs_ub.txt 2>&1 &
  nohup python quantiles.py configs/${config_file}_costs_lb.yml --suffix=_${age}_costs_lb global_interaction_Tmean-${filespec}-AgeSpec-${age}-costs${suff} > ${dirlog}/${runs}/${spec}/${levrat}_${vals}_${age}_costs_lb.txt 2>&1 &
  nohup python quantiles.py configs/${config_file}.yml --suffix=_${age}_noadapt global_interaction_Tmean-${filespec}-AgeSpec-${age}-noadapt${suff} > ${dirlog}/${runs}/${spec}/${levrat}_${vals}_${age}_noadapt.txt 2>&1 &
  nohup python quantiles.py configs/${config_file}.yml --suffix=_${age}_incadapt global_interaction_Tmean-${filespec}-AgeSpec-${age}-incadapt${suff} > ${dirlog}/${runs}/${spec}/${levrat}_${vals}_${age}_incadapt.txt 2>&1 &
done
