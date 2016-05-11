#!/bin/bash
source ~/aggregator/env/bin/activate
cd ..

for i in {1..10}
do
    nohup python -m generate.montecarlo /shares/gcp/outputs/nasmort-fireant >& montecarlo$i.log &
    sleep 5
done


