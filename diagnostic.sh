#!/bin/bash
python2.7 -m generate.generate $1 --filter-region=USA --outputdir=$PWD/temp --singledir=single --mode=writecalcs
