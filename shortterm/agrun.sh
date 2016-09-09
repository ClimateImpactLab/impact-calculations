#!/bin/bash

source /home/jrising/aggregator/env/bin/activate
cd ..
nohup python -m shortterm.aggregate /shares/gcp/outputs/conflict/impacts-formosan >& ag1.log &




