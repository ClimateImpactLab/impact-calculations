source ~/aggregator/env/bin/activate
cd ..

nohup python -m generate.aggregate /shares/gcp/outputs/nasmort-clipped2 >& aggregate.log &



