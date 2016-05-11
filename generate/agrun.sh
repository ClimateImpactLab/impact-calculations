source ~/aggregator/env/bin/activate
cd ..

nohup python -m generate.aggregate /shares/gcp/outputs/nasmort-fireant >& aggregate.log &



