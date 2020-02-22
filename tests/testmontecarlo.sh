#!/bin/bash
# Hack script so that monte carlo system test will run.

python -m generate.generate $1 --filter-region=USA.14.608 --outputdir=$PWD/temp 
