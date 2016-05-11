#!/bin/bash
cd ..

nohup python -m generate.montecarlo /mnt/gcp/output-fireant >& montecarlo1.log &
sleep 5
nohup python -m generate.montecarlo /mnt/gcp/output-fireant >& montecarlo2.log &
sleep 5
nohup python -m generate.montecarlo /mnt/gcp/output-fireant >& montecarlo3.log &
sleep 5
nohup python -m generate.median /mnt/gcp/output-fireant >& median4.log &

