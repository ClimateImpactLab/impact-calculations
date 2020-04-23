from impactlab_tools.utils import files

with open(files.sharedpath("outputs/testthis.txt"), 'w') as fp:
    fp.write("It works!\n")

