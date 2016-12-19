#!/bin/bash
source ~/aggregator/env/bin/activate
nohup python -m generate.generate $1 >& $2.log &
