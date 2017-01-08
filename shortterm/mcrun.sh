source ~/aggregator/env/bin/activate
cd ..
nohup python -m shortterm.montecarlo /shares/gcp/outputs/conflict/impacts-legionary >& logs/conflict-montecarlo.log &




