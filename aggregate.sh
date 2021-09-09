#!/bin/bash
# Aggregate results produced by the generate.sh script to largers spatial resolutions.
# 
# Syntax:
#   ./aggregate.sh <config> [<#>] ...
# 
# The <config> configuration file should be an aggregation
# configuration file. See docs/aggregator.sh.
# The option <#> argument starts up multiple CPUs, if this is not run on BRC.
# Additional arguments (...) are configuration options, specified as "--key=value".

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
