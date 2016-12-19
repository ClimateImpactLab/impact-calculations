#!/bin/bash
source ~/aggregator/env/bin/activate

for i in {1..10}
do
    nohup python -m generate.generate $1 >& $2$i.log &
    sleep 5
done


