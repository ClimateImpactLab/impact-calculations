import os

def sharedpath(subpath):
    return os.path.join('/shares/gcp', subpath)

if __name__ == '__main__':
    os.chdir("/shares/gcp")
    print datapath('testing')
