#!/bin/bash

for i in {1..10}
do
    nohup python -m generate.generate $1 &
    sleep 5
done


