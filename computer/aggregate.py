import servers
from lib.task import SingleCPUTask, LambdaDependency, LambdaTask, unimplemented_task, noop_task

def prepare_gcp_generation(server):
    if server.utup == ('berkeley', 'shackleton'):
        server.run_command("source ../../../../env/bin/activate", 'src')
    elif server.utup == ('brc', 'savio'):
        server.run_commands("""
module load python/2.7.8
module load virtualenv

cd ~/gcp/src
source ../env/bin/activate

module load numpy
module load hdf5
module load netcdf
""")

has_gcp_data = LambdaDependency("GCP Data",
                                lambda server: server.has_file('climate', 'grid2reg') and server.has_file('data', 'baselines'))
has_gcp_code = LambdaDependency("GCP Code",
                                lambda server: server.has_file('src', 'generate') and server.has_file('openest', 'models'))
is_gcp_generable = LambdaDependency("GCP Environment",
                                    lambda server: True, atrun_func=prepare_gcp_generation)

dependencies = [has_gcp_data, has_gcp_code, is_gcp_generable]

aggregate_task = LambdaTask(dependencies, lambda server: server.start_process("python -m generate.aggregate " + server.roots['output']))

for server, name in servers.all_osdc():
    print(name)
    server.connect()

    server.verbose = True

    aggregate_task.prepare(server)
    aggregate_task.fullrun(server, doublecheck=False)
