source ~/aggregator/env/bin/activate
cd ..

nohup python -m generate.aggregate /shares/gcp/outputs/mortality/impacts-pharaoh >& agmortality.log &
nohup python -m generate.aggregate /shares/gcp/outputs/labor/impacts-andrena >& aglabor.log &
