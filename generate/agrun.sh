source ~/aggregator/env/bin/activate
cd ..

nohup python -m generate.aggregate /shares/gcp/outputs/mortality/impacts-pharaoh >& aggregate.log &



