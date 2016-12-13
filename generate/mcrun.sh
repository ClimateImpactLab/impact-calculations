#!/bin/bash
source ~/aggregator/env/bin/activate
cd ..

for i in {1..10}
do
    nohup python -m generate.generate montecarlo mortality /shares/gcp/outputs/nasmort-pharaoh >& montecarlo$i.log &
    sleep 5
done


