#!/bin/bash
# Job name:
#SBATCH --job-name=mortality-montecarlo
# Partition:
#SBATCH --partition=savio2_bigmem
# Account:
#SBATCH --account=co_laika
# QoS:
#SBATCH --qos=laika_bigmem2_normal
# Wall clock limit:
#SBATCH --time=36:00:00

## Command(s) to run:
module load python/2.7.8
module load virtualenv

source ../env/bin/activate

module load numpy

for i in {1..4}
do
  python -m generate.generate configs/mortality-montecarlo.yml &
  sleep 5
  # python -m generate.generate configs/labor-montecarlo.yml &
  # sleep 5
done

python -m generate.generate configs/mortality-montecarlo.yml

python -m generate.aggregate configs/mortality-aggregate.yml
