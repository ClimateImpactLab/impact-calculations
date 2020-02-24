import osdc_server

credentials = {'username': 'jrising', 'instanceip': '172.17.192.44', 'loginnode': 'griffin.opensciencedatacloud.org'}
roots = {'data': '/mnt/gcp/data', 'climate': '/mnt/gcp/BCSD', 'src': '/home/ubuntu/gcp/src', 'openest': '/home/ubuntu/gcp/open-estimate'}

server = osdc_server.OSDCServer(4, roots, credentials)
server.connect()

def code_update():
    print(server.run_command("with_proxy git pull", 'openest')[0])
    print(server.run_command("with_proxy git pull", 'src')[0])

print(server.run_command("sudo chown ubuntu:ubuntu /mnt"))
print(server.run_command("ssh-keyscan 172.17.192.44 >> ~/.ssh/known_hosts"))
process = server.start_process("rsync -avz 172.17.192.44:/mnt/gcp /mnt/")
server.read_file(process.logfile)

print(server.run_command("scp 172.17.192.44:~/gcp/src/generate/mcrun.sh generate/mcrun.sh", 'src'))
print(server.run_command("cd generate; with_proxy ./mcrun.sh", 'src'))

# ssh -A jrising@griffin.opensciencedatacloud.org
# ssh -A ubuntu@
