from impactlab_tools.utils import paralog

class NoClaimStatusManager:
    def __init__(self, jobname, jobtitle, logdir, timeout, exclusive_jobnames=None):
        self.jobname = jobname
        self.timeout = timeout
        self.exclusive_jobnames = exclusive_jobnames if exclusive_jobnames is not None else []
    
    def claim(self, dirpath):
        if not os.path.exists(dirpath):
            return True
        elif self.is_claimed(dirpath):
            return False

        return True

    def is_claimed(self, dirpath):
        if not os.path.exists(dirpath):
            return False
        
        for jobname in [self.jobname] + self.exclusive_jobnames:
            filepath = paralog.StatusManager.claiming_filepath(dirname, jobname)
            if os.path.exists(filepath):
                if time.time() - os.path.getmtime(filepath) < self.timeout:
                    return True

        return False

    def release(dirpath, status):
        pass

class NoWriteDataset:
    def __init__(self, filepath, mode, format='NETCDF4'):
        pass

    def createDimension(self, dimname, size=None):
        pass

    def createVariable(self, varname, datatype, **kwargs):
        return NoWriteVariable(varname, datatype)

    def close(self):
        pass

class NoWriteVariable:
    def __init__(self, varname, datatype):
        pass

    def __setitem__(self, key, value):
        pass
    
