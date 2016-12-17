import os

def sharedpath(subpath):
    return os.path.join(server_config['shared_dir'], subpath)

if __name__ == '__main__':
    print datapath('testing')
