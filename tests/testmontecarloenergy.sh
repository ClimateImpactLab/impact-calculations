#!/bin/bash
# Hack script so that monte carno energy system test will work.

python -m generate.generate $1 --filter-region=USA.14.608 --outputdir=$PWD/temp 

