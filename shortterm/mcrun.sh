source ~/aggregator/env/bin/activate
cd ..
nohup python -m shortterm.montecarlo /shares/gcp/outputs/conflict/impacts-coconut >& logs/conflict-montecarlo.log &




