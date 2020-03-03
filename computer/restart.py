import servers

for server, name in servers.all_osdc():
    print(name)
    server.connect()

    #print server.run_command("killall python")[0]
    print((server.run_command("rm -r /mnt/gcp/output-clipped2")[0]))
    #print server.run_command("with_proxy git pull", 'openest')[0]
    #print server.run_command("git stash; with_proxy git pull; git stash apply", 'src')[0]
    #print server.run_command("scp 172.17.192.43:~/gcp/src/generate/loadmodels.py generate/", 'src')[0]
    #print server.run_command("cd generate; chmod a+x osdcrun.sh; with_proxy ./osdcrun.sh", 'src')[0]

"""
172.17.192.43, 172.17.192.30, 172.17.192.40, 172.17.192.18, 172.17.192.44, 172.17.192.45, 172.17.192.3

ssh -A jrising@griffin.opensciencedatacloud.org
ssh -A ubuntu@172.17.192.43

killall python
mv /mnt/gcp/output /mnt/gcp/output-postsur

cd gcp/open-estimate
with_proxy git pull

cd ../src
# git config credential.helper store
git stash
with_proxy git pull
git stash apply

with_proxy rsync -avz jrising@dmas.berkeley.edu:/shares/gcp/data/ ../data/
# rsync -avz 172.17.192.30:~/gcp/data/ ../data/

# scp 172.17.192.43:~/gcp/src/generate/loadmodels.py generate/loadmodels.py
# scp 172.17.192.43:~/gcp/src/generate/montecarlo.py generate/montecarlo.py

rm *.log
cd generate; with_proxy ./mcrun.sh
"""
"""
rm ~/gcp/data/adaptation/predictors-space-all/*
rm ~/gcp/data/adaptation/predictors-space-65+/*
# with_proxy rsync -avz jrising@dmas.berkeley.edu:/shares/gcp/data/ gcp/data/
rsync -avz 172.17.192.30:~/gcp/data/ gcp/data/
"""
