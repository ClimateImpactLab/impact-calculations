"""
This code should be run from the command line with a config yml file. The yml file should contain (most are identical to the aggregation.py parameters) : 
    - outputdir
    - targetdirs : the path to a csv file that lists the target directories to run
    - weighting
    - only_variables
    - basename
    - processes : number of processes to run in parallel. Each process takes care of one target directory.

Run this code that way : 

python -m generate.apply_aggregate {config.yml}

"""

import sys
import glob
import multiprocessing
import csv
import pandas as pd
import os
from itertools import product
from joblib import Parallel, delayed

def ParseVariables(variables):

    """Turns a list of variables to a string that can be used as the 'only-variables' parameter to the aggregation code through a command line
    execution
    """
    Parser = "["
    i = 0
    for var in variables:
        i = i + 1
        Parser = Parser+ "'" + var + "'"
        if i<len(variables):
            Parser = Parser + ","

    Parser = Parser+"]"

    return Parser


def DoAggregate(outputdir, targetdir, weighting, only_variables, basename, check_variable='rebased'):

    """Sends a command line python execution of the aggregation code. 
    """
    os.system('python -m generate.aggregate' + 
              ' --outputdir=' + outputdir + 
              ' --targetdir=' + targetdir + 
              ' --weighting=' + weighting + 
              ' --only-variables=' + only_variables +
              ' --basename=' + basename +
              ' --check-variable=' + check_variable)
    

def ReadTargets(file):
    """Reads a csv file containing a single column and > 0 number of rows, each containing the full path of a target directory.

    Parameters
    ----------
    file : str - full path to a target dir, up to the SSP included.

    Requires
    -------
    file :  the list of paths must not contain duplicate, and start from the root, without a last trailing slash. for example :
    '/mnt/battuta_shares/gcp/outputs/agriculture/impacts-mealy/rice-median-291020/median/rcp85/surrogate_MRI-CGCM3_11/low/SSP3'

    Returns
    -------
    a python list containing the target directories.
    """

    return pd.read_csv(file)['targetdir'].tolist()

if __name__ == "__main__": 

    """Runs an aggregation over a list of targetdirs defined in a csv file. Runs with a config.
    """

    import yaml
    with open(str(sys.argv[1]), 'r') as file:
        config = yaml.load(file)
        assert 'outputdir' in config

    assert all(x in config for x in ['outputdir','targetdirs', 'weighting', 'only-variables','basename','processes', 'check-variable']), 'incomplete configurations file'

    outputdir = config.get('outputdir')
    targetdirs= ReadTargets(config.get('targetdirs'))
    weighting= config.get('weighting')
    only_variables= ParseVariables(config.get('only-variables'))
    basename= config.get('basename')
    processes= int(config.get('processes'))
    check_variable=config.get('check-variable')

    with Parallel(n_jobs=processes) as parallelize:
        parallelize(delayed(DoAggregate)(outputdir, target, weighting, only_variables, basename, check_variable) for target in targetdirs) 
