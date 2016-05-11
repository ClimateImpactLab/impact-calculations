import paramiko, getpass
from paramiko_server import ParamikoServer

class LoginServer(ParamikoServer):
    def __init__(self, utup, cpus, roots, credentials):
        super(LoginServer, self).__init__(utup, cpus, roots, credentials)
        self.password = getpass.getpass("Password for " + credentials['domain'] + ": ")

    def connect(self):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.credentials['domain'], username=self.credentials['username'], password=self.password)
        # Open up a session
        s = client.get_transport().open_session()
        paramiko.agent.AgentRequestHandler(s)

        s.get_pty()
        s.invoke_shell()

        self.client = client
        self.session = s
        self.connected = True

        self.receive_all()
