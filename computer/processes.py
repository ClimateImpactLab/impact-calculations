import cmd, sys, os, signal
import subprocess

class Manager(cmd.Cmd):
    def __init__(self, silent):
        cmd.Cmd.__init__(self)
        self.silent = silent
    
    def do_show(self, line):
        processes = subprocess.Popen(['ps', '-Af'], stdout=subprocess.PIPE).stdout.read().split('\n')

        mine = [line for line in processes if line[:7] == 'jrising' and 'python' in line]
        self.pids = [line.split()[1] for line in mine]
        self.commands = [line[line.index('python'):] for line in mine]
        self.unique = set(self.commands)
        self.unique.discard('python processes.py')

        if not self.silent:
            for command in self.unique:
                print((self.commands.count(command), command))

    def do_kill(self, arg):
        for pid in [int(self.pids[ii]) for ii in range(len(self.commands)) if self.commands[ii] == arg]:
            if not self.silent:
                print(("Killing %d" % pid))
            os.kill(pid, signal.SIGTERM)

    def complete_kill(self, text, line, begidx, endidx):
        possibles = list(self.unique)
        for chunk in line.split()[1:-1]:
            possibles = [possible[len(chunk)+1:] for possible in possibles if possible[:len(chunk)] == chunk]

        return [possible for possible in possibles if possible[:len(text)] == text]

if __name__ == '__main__':
    mngr = Manager(False)
    mngr.do_show(None)
    mngr.cmdloop()
