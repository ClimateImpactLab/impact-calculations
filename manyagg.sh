#!/bin/bash

for i in {1..5}
do
    nohup python -m generate.aggregate $1 &
    sleep 5
done


