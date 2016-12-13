#!/bin/bash
source ~/aggregator/env/bin/activate
cd ..
python -m generate.generate median mortality /shares/gcp/outputs/mortality/impacts-pharaoh
