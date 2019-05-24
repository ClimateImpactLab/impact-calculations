#!/bin/bash

if [ "$#" -ne 1 ]; then
    for ln in $(seq 0 8); do
	if [ `hostname` = "ln00$ln.brc" ]; then
	   echo "Cannot run aggregate processes in the background of the BRC login node!"
	   exit
	fi
    done
    for i in $(seq 1 $2); do
	nohup python -m generate.aggregate $1 "{@:3}" > /dev/null 2>&1 &
	sleep 5
    done
else
    python -m generate.aggregate $1 "{@:3}"
fi
