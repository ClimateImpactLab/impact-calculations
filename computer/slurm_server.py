from login_server import LoginServer

class SlurmServer(LoginServer):
    def __init__(self, utup, cpus, roots, credentials):
        super(SlurmServer, self).__init__(utup, cpus, roots, credentials)

    def active_processes(self, procname):
        # Ignores procname
        return int(self.run_command("squeue | grep $USER | wc -l")[0])
