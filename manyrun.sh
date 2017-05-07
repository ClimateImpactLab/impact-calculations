#!/bin/bash

logpath1=${1/configs/logs}
logpath2=${logpath/.yml/}
for i in {1..10}
do
    nohup python -m generate.generate $1 >& $logpath2$i.log &
    sleep 5
done


