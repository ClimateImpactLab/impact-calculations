import osdc_server, login_server, slurm_server

def all_osdc():
    ips = ['172.17.192.43', '172.17.192.30', '172.17.192.40', '172.17.192.18', '172.17.192.44', '172.17.192.45', '172.17.192.3']

    for ip in ips:
        credentials = {'username': 'jrising', 'instanceip': ip, 'loginnode': 'griffin.opensciencedatacloud.org'}
        roots = {'data': '/mnt/gcp/data', 'climate': '/mnt/gcp/BCSD', 'src': '/home/ubuntu/gcp/src', 'openest': '/home/ubuntu/gcp/open-estimate', 'output': '/mnt/gcp/output-fireant'}

        server = osdc_server.OSDCServer(('osdc', ip), 4, roots, credentials)
        yield server, server.credentials['instanceip']

def all_linux():
    credentials = {'username': 'jrising', 'domain': 'dmas.berkeley.edu'}
    roots = {'data': '/shares/gcp/data', 'climate': '/shares/gcp/BCSD', 'src': '~/aggregator/trunk/ext/gcp/src', 'openest': '~/aggregator/trunk/lib', 'output': '/shares/gcp/outputs/nasmort-fireant'}

    server = login_server.LoginServer(('berkeley', 'shackleton'), 20, roots, credentials)
    yield server, "DMAS"

    return # No longer using BRC

    credentials = {'username': 'jrising', 'domain': 'hpc.brc.berkeley.edu'}
    roots = {'data': '/global/scratch/jrising/data', 'climate': '/global/scratch/jrising/BCSD', 'src': '~/gcp/src', 'openest': '~/gcp/open-estimate', 'output': '/global/scratch/jrising/outputs'}

    server = slurm_server.SlurmServer(('brc', 'savio'), 20, roots, credentials)
    yield server, "Savio"

def all():
    for server, name in all_linux():
        yield server, name

    for server, name in all_osdc():
        yield server, name

