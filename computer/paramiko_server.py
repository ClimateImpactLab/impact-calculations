import sys, time
import paramiko
from lib.linux_server import SizelessLinuxServer

class ParamikoServer(SizelessLinuxServer):
    def receive(self):
        stdout = ""
        while self.session.recv_ready():
            stdout += self.session.recv(sys.maxint)

        stderr = ""
        while self.session.recv_stderr_ready():
            stderr += self.session.recv_sterr(sys.maxint)

        return stdout, stderr

    def receive_all(self):
        stdout = ""
        stderr = ""

        while stdout[-2:] != '$ ':
            time.sleep(0.1)
            stdout2, stderr2 = self.receive()
            stdout += stdout2
            stderr += stderr2

        return stdout, stderr

    def receive_each(self):
        stdout = ""
        while stdout[-2:] != '$ ':
            time.sleep(0.1)
            stdout, stderr = self.receive()
            yield stdout, stderr

    def disconnect(self):
        self.client.close()
        self.connected = False

    def run_command(self, command, root=None, path=None):
        "Returns (output, error) as strings."

        stdout = ""
        stderr = ""
        for stdout2, stderr2 in self.run_command_each(command, root, path):
            stdout += stdout2
            stderr += stderr2
        stdout = "\n".join(stdout.split('\r\n')[1:-1]) # drop command and prompt

        return stdout, stderr

    def run_command_each(self, command, root=None, path=None):
        if root is not None:
            self.cwd(self.fullpath(root, path))

        print command

        self.session.sendall(command + '\n')
        for stdout, stderr in self.receive_each():
            yield stdout, stderr
