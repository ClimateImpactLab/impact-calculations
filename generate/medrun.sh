source ~/aggregator/env/bin/activate
cd ..
#python -m generate.median /shares/gcp/outputs/nasmort

for i in {1..5}
do
    nohup python -m generate.median /shares/gcp/outputs/tmp >& median$i.log &
    sleep 5
done


