import os
import config

def sharedpath(subpath):
    return os.path.join(config.serverConfig['shareddir'], subpath)

if __name__ == '__main__':
    print datapath('testing')
