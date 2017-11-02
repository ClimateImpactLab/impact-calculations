#!/bin/bash
# Job name:
#SBATCH --job-name=mortality-montecarlo
# Partition:
#SBATCH --partition=savio2
# OR savio2_bigmem
# Account:
#SBATCH --account=co_laika
# QoS:
#SBATCH --qos=savio_lowprio
# OR laika_bigmem2_normal
# Wall clock limit:
#SBATCH --time=24:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1

## Command(s) to run:
module load python/2.7.8
module load virtualenv

source ../env/bin/activate

module load numpy

python -m generate.generate configs/mortality-montecarlo.yml


