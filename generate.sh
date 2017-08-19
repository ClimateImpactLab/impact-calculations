#!/bin/bash

if [ "$#" -ne 1 ]; then
    for i in {1..$2}
    do
	nohup python -m generate.generate $1 &
	sleep 5
    done
else
    python -m generate.generate $1
fi
