"""
Compute minutes lost due to temperature effects
"""

import numpy as np
from openest.generate.stdlib import *
from adaptation import csvvfile

def prepare_csvv(csvvpath, qvals, callback):
    data = csvvfile.read(csvvpath)

    polynomial_weather - [27, 27**2, 27**3, 27**4]
