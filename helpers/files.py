import os

def sharedpath(subpath):
    return os.path.join(serverConfig['shareddir'], subpath)

if __name__ == '__main__':
    print datapath('testing')
