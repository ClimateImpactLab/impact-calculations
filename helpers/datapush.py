import sys, tempfile, os
import datafs, header

filename = sys.argv[1]

api = datafs.get_api()

assert filename[:8] == '/shares/'

with open(filename, 'r') as fp:
    metadata = header.parse(fp)
    for var in metadata['variables']:
        metadata['variables'][var] = "%s [%s]" % (metadata['variables'][var].description, metadata['variables'][var].unit)

    tempfp, temppath = tempfile.mkstemp()
    for line in fp:
        os.write(tempfp, line)
    os.close(tempfp)

archive = api.create(filename[8:], metadata=metadata)
archive.update(temppath)

os.unlink(temppath)
