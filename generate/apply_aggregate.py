import sys
import glob
import multiprocessing
import csv
import pandas as pd
import os
from itertools import product

def ParseVariables(variables):

    Parser = "["
    i = 0
    for var in variables:
        i = i + 1
        Parser = Parser+ "'" + var + "'"
        if i<len(variables):
            Parser = Parser + ","

    Parser = Parser+"]"

    return Parser


def DoAggregate(outputdir, targetdir, weighting, only_variables, basename):


    os.system('python -m generate.aggregate' + 
              ' --outputdir=' + outputdir + 
              ' --targetdir=' + targetdir + 
              ' --weighting=' + weighting + 
              ' --only-variables=' + only_variables +
              ' --basename=' + basename)
    

def ReadTargets(file):
    """Reads a csv file containing a single column : the full path of a target directory.

    Parameters
    ----------
    file : str - full path to a target dir, up to the SSP, included.

    Requires
    -------
    file :  the list of paths must not contain duplicate, and start from the root, without a last trailing slash. for example :
    '/mnt/battuta_shares/gcp/outputs/agriculture/impacts-mealy/rice-median-291020/median/rcp85/surrogate_MRI-CGCM3_11/low/SSP3/'

    Returns
    -------
    a python list containing the target directories.
    """

    return pd.read_csv(file)['targetdir'].tolist()

if __name__ == "__main__":  
    """Runs an aggregation over a list of targetdirs
    """
    outputdir=sys.argv[1]
    targets=ReadTargets(sys.argv[2])
    weighting=sys.argv[3]
    only_variables=ParseVariables(sys.argv[4].split(','))
    basename=sys.argv[5]
    for target in targets:
        print("doing " + target)
        DoAggregate(outputdir, target, weighting, only_variables, basename)

    # with multiprocessing.Pool(processes=nb_processes) as pool:
    #     pool.starmap(DoAggregate, product(outputdir, targets, weighting, only_variables, basename))
