# NOTE: after every restart, need to call
# ssh-add ~/.ssh/laptop2.pem

import servers

medians = 0
batches = 0
processes = 0
for server, name in servers.all():
    server.connect()

    try:
        median_count = int(server.run_command("find " + server.fullpath('output') + "/median -name \"*.yml\" | wc -l")[0])
        batchs_count = int(server.run_command("find " + server.fullpath('output') + "/batch* -name \"*.yml\" | wc -l")[0])
        process_count = server.active_processes('generate.')
        print((name, median_count, batchs_count, process_count))
        medians += median_count
        batches += batchs_count
        processes += process_count
    except Exception as ex:
        print(ex)

print((medians, batches, processes))
