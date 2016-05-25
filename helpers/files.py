import os, inspect

class Anchor: pass

def datapath(subpath):
    return os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../data", subpath))

if __name__ == '__main__':
    os.chdir("/shares/gcp")
    print datapath('testing')
