#!/bin/bash
# Job name:
#SBATCH --job-name=impact-calculations
# Partition:
#SBATCH --partition=savio2_bigmem
# Account:
#SBATCH --account=co_laika
# QoS:
#SBATCH --qos=laika_bigmem2_normal
# Wall clock limit:
#SBATCH --time=52:00:00

## Command(s) to run:
module load python/2.7.8
module load virtualenv

source ../../env/bin/activate

module load numpy
module load hdf5
module load h5py

for i in {1..23}
do
  python -m generate.generate configs/energy-median.yml &
  sleep 5
done

python -m generate.generate configs/energy-median.yml

#python -m generate.aggregate configs/mortality-aggregate.yml
