#!/bin/bash
source ~/aggregator/env/bin/activate
cd ..
python -m generate.generate writebins mortality /shares/gcp/outputs/mortality/impacts-pharaoh
