from netCDF4 import Dataset
import os, sys

def compare2ncdf(file1, file2):
    """
    Return (error) code corresponding to:
    0 -> The two files are the same
    1 -> Missing variables
    2 -> Missing years
    3 -> Missing regions
    4 -> The two data files are different
    5 -> Missing file, and its not caught by netCDFComparerFeeder (bug)
    """
    try:
        ncd1 = Dataset(file1, 'r', format='NETCDF4')
    except:
        return (5, file1, "", "", "")
    try:
        ncd2 = Dataset(file2, 'r', format='NETCDF4')
    except:
        return (5, file2, "", "", "")

    dimensions = set(ncd1.variables) | set(ncd2.variables)

    for dmsn in dimensions:
        if dmsn not in ncd1.variables:
             return (1, file1, dmsn, "", "")
        if dmsn not in ncd2.variables: 
             return (1, file2, dmsn, "", "")

        if len(ncd1.variables[dmsn]) != len(ncd2.variables[dmsn]):
            return (2, file1, dmsn, "", "")

            for year in range(len(ncd1.variables[dmsn])):
                if len(ncd1.variables[dmsn][year]) != len(ncd2.variables[dmsn][year]):
                    return (3, file1, dmsn, year, "")
                for region in range(len(ncd1.variables[dmsn][year])):
                    if ncd1.variables[dmsn][year][region] != ncd2.variables[dmsn][year][region]:
                        return (4, file1, dmsn, year, region)
    return (0, "", "", "", "")


def netCDFComparerFeeder(basedir1, basedir2, targetFileName):
    """
    Search the two basedir for targetFileName, and use set union to check if missing anything. 
    """
    # Run through all subdirs of both basedirs to hunt for target.
    # Use "set union minus set intersection" to identify missing files. 
    dir1, dir2 = [], []
    for root, dirs, files in os.walk(basedir1):
        if targetFileName in files:
            dir1.append(root[len(basedir1):].lstrip("/"))

    for root, dirs, files in os.walk(basedir2):
        if targetFileName in files:
            dir2.append(root[len(basedir2):].lstrip("/"))
    
    set1, set2 = set(dir1), set(dir2)
    commList = set1 & set2
    diffList = (set1 | set2) - commList

    if diffList:
        print("Missing files:")
        for diffFile in diffList:
            if diffFile in dir1:
                print(("%s missing: %s" % (basedir1, diffFile)))
            else:
                print(("%s missing: %s" % (basedir2, diffFile)))

    missingVar = []
    missingYear = []
    missingRegn = []
    diffData = []
    for path in commList:
        code, filex, dmsn, year, regn = compare2ncdf(os.path.join(basedir1, path, targetFileName), os.path.join(basedir2, path, targetFileName))
        if code == 1:
            missingVar.append((filex, dmsn))
        elif code == 2:
            missingYear.append((filex, dmsn))
        elif code == 3:
            missingRegn.append((filex, dmsn, year))
        elif code == 4:
            diffData.append((filex, dmsn, year, regn))

    if missingVar:
        print("Files Missing Vars:")
        for filex in missingVar:
            print(("%s missing: %s" % (filex[0], filex[1])))
    if missingYear:
        print("Vars Missing Year (Check both basedirs):")
        for filex in missingYear:
            print(("%s has weird year counts for %s" % (filex[0], filex[1])))
    if missingRegn:
        print("Vars Missing Region:")
        for filex in missingRegn:
            print(("%s has weird region counts for year %s, %s" % (filex[0], filex[2], filex[1])))
    if diffData:
        print("Files are different:")
        for filex in missingRegn:
            print(("Data of %s is different for %s, year %s, region %s" % (filex[0], filex[1], filex[2], filex[3])))
    return 


if __name__ == "__main__":
    netCDFComparerFeeder(sys.argv[1], sys.argv[2], sys.argv[3])
