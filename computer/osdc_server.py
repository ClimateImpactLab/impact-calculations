import paramiko
from paramiko_server import ParamikoServer
from lib.process import SingleCPUProcess

class OSDCProcess(SingleCPUProcess):
    def __init__(self, pid, logfile):
        super(OSDCProcess, self).__init__(logfile)
        self.pid = pid

    def is_running(self):
        raise NotImplementedError("Not implemented yet.")

    def kill(self):
        raise NotImplementedError("Not implemented yet.")

    def clean(self):
        raise NotImplementedError("Not implemented yet.")

class OSDCServer(ParamikoServer):
    def __init__(self, utup, cpus, roots, credentials):
        super(OSDCServer, self).__init__(utup, cpus, roots, credentials)

    def connect(self):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # ssh -A jrising@griffin.opensciencedatacloud.org
        client.connect(self.credentials['loginnode'], username=self.credentials['username'])
        # Open up a session
        s = client.get_transport().open_session()
        paramiko.agent.AgentRequestHandler(s)

        s.get_pty()
        s.invoke_shell()

        self.client = client
        self.session = s

        # ssh -A ubuntu@172.17.192.44
        stdout, stderr = self.run_command('ssh -A ubuntu@' + self.credentials['instanceip'])

        self.connected = True
