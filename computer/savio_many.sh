#!/bin/bash

for i in {1..20}
do
    sbatch savio_single.sh
    #sbatch savio_onecpu.sh
    sleep 5
done
