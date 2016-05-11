import servers, time, sys

def mysend(session, command, response=None):
    server.session.sendall(command)

    stdout = "none"
    while stdout[-2:] != '$ ':
        if server.session.recv_ready():
            stdout = server.session.recv(sys.maxint)

            if len(stdout) == 0:
                pass
            elif stdout[-2:] == ': ':
                if response is None:
                    response = raw_input(stdout)
                server.session.sendall(response + '\n')
            elif stdout[-2:] == '? ':
                server.session.sendall('yes\n')
            else:
                print stdout

        time.sleep(0.1)

response = raw_input("Password: ")

for server, name in servers.all_osdc():
    print name
    server.connect()
    if name in ["172.17.192.43", "172.17.192.44"]:
        mysend(server.session, "with_proxy rsync -avz /mnt/gcp/output-clipped2/batch0/ 172.17.192.30:/mnt/gcp/output-clipped2/" + name + "-batch0/\n", response=response)
        mysend(server.session, "with_proxy rsync -avz /mnt/gcp/output-clipped2/median/ 172.17.192.30:/mnt/gcp/output-clipped2/" + name + "-median/\n", response=response)
        mysend(server.session, "find /mnt/gcp/output-clipped2/ -name \"*.nc4\" -exec rm {} \\;\n")
    else:
        mysend(server.session, "with_proxy rsync -avz /mnt/gcp/output-clipped2/batch0/ jrising@169.229.150.107:~/projects/gcp/nasmort-clipped2/" + name + "-batch0/\n", response=response)
        mysend(server.session, "with_proxy rsync -avz /mnt/gcp/output-clipped2/median/ jrising@169.229.150.107:~/projects/gcp/nasmort-clipped2/" + name + "-median/\n", response=response)
        #mysend(server.session, "rm -r /mnt/gcp/output-clipped2/batch0/\n", response=response)
        #mysend(server.session, "rm -r /mnt/gcp/output-clipped2/median/\n", response=response)

for server, name in servers.all_osdc():
    if name == "172.17.192.30":
        server.connect()
        mysend(server.session, "with_proxy rsync -avz /mnt/gcp/output-clipped2/*-batch0 jrising@169.229.150.107:~/projects/gcp/nasmort-clipped2/\n", response=response)
        mysend(server.session, "with_proxy rsync -avz /mnt/gcp/output-clipped2/*-median jrising@169.229.150.107:~/projects/gcp/nasmort-clipped2/\n", response=response)
        mysend(server.session, "find /mnt/gcp/output-clipped2/*-batch0 -name \"*.nc4\" -exec rm {} \\;\n")
        mysend(server.session, "find /mnt/gcp/output-clipped2/*-median -name \"*.nc4\" -exec rm {} \\;\n")

# with_proxy rsync -avz /mnt/gcp/output-allbins/batch0 jrising@dmas.berkeley.edu:/shares/gcp/outputs/nasmort-allbins/

# Also do:
# ssh jrising@dtn.brc.berkeley.edu
# rsync -avz /global/scratch/jrising/outputs/batch3/ jrising@dmas.berkeley.edu:/shares/gcp/outputs/nasmort/brc-batch3/

"""


import servers, sys
iter = servers.all_osdc()
server, name = iter.next()
server, name = iter.next()
server.connect()
command = "with_proxy rsync -avz batch0/ jrising@dmas.berkeley.edu:/shares/gcp/outputs/nasmort/" + name + "-batch0/"
server.session.sendall(command + '\n')
server.session.recv(sys.maxint)
server.session.recv_ready()
server.session.sendall('p15au3t\n')
"""


"""



with_proxy rsync -avz batch0/ jrising@dmas.berkeley.edu:/shares/gcp/outputs/nasmort/172.17.192.43-batch0/

exit
ssh -A ubuntu@172.17.192.30
cd /mnt/gcp/output
with_proxy rsync -avz 172.17.192.44-batch0/ jrising@dmas.berkeley.edu:/shares/gcp/outputs/nasmort/172.17.192.44-batch0/
"""
