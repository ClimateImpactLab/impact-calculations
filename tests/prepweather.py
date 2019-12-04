import os
from shutil import copyfile
from netCDF4 import Dataset

sourcedir = '/shares/gcp/climate/BCSD/hierid/popwt/daily/tas/'
targetdir = 'testdata/climate/BCSD/hierid/popwt/daily/tas/'

gcm = 'CCSM4'

for scenario in os.listdir(sourcedir):
    if not os.path.isdir(os.path.join(sourcedir, scenario)):
        continue
    for year in os.listdir(os.path.join(sourcedir, scenario, gcm)):
        srcpath = os.path.join(sourcedir, scenario, gcm, year)
        dstpath = os.path.join(targetdir, scenario, gcm, year)
        if not os.path.exists(dstpath):
            os.makedirs(dstpath)
        for filename in os.listdir(srcpath):
            if filename[:-4] == '1.5' or os.path.isdir(os.path.join(srcpath, filename)):
                continue # we have 1.6
            print os.path.join(dstpath, filename)
            if filename[-4:] == '.nc4':
                reader = Dataset(os.path.join(srcpath, filename), 'r', format='NETCDF4')
                writer = Dataset(os.path.join(dstpath, filename), 'w', format='NETCDF4')

                writer.createDimension('time', None)
                writer.createDimension('hierid', 1)
                
                for key in reader.variables.keys():
                    if key == 'time':
                        column = writer.createVariable(key, 'f4', (key,))
                        column[:] = reader.variables[key][:]
                    elif key == 'hierid':
                        column = writer.createVariable(key, str, ('hierid',))
                        column[0] = 'dummy'
                    else:
                        column = writer.createVariable(key, 'f4', ('time', 'hierid'))
                        column[:, :] = reader.variables[key][:, 1000:1001]
                        
                reader.close()
                writer.close()
            else:
                copyfile(os.path.join(srcpath, filename), os.path.join(dstpath, filename))
