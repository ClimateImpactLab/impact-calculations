"""Helper functions for handling IR-constant values.
"""

import numpy as np
import pandas as pd
from impactlab_tools.utils import files

def load_culture_data(filepath, plantcol, harvestcol, yearlen):
    """Load planting and harvesting (cultivation) date data.

    In cases where the harvest date is before to the planting date
    (the cultivation dates span a year boundary), the harvest date is
    shifted by `yearlen` so that it will be after the planting date.

    Parameters
    ----------
    filepath : str
        Shared directory or full path to the cultivation data.
    plantcol : str
        The name of the planting date column.
    harvestcol : str
        The name of the harvesting date column.
    yearlen : int
        The length of the year, in the units represented in the colums.

    Returns
    -------
    dict(str, tuple(int, int))
        A dictionary that maps IR region names to cultivation dates.
    """
    df = pd.read_csv(files.sharedpath(filepath), index_col='hierid')

    culture_data = {}
    # Loop through rows/regions
    for index, row in df.iterrows():
        if not np.isnan(row[plantcol]) and not np.isnan(row[harvestcol]):
            plant = int(row[plantcol])
            harvest = int(row[harvestcol])
            if harvest < plant:
                harvest += yearlen
            culture_data[index] = plant, harvest

    return culture_data

def load_culture_months(filepath):
    """Extract cultivation months from the given filepath."""
    
    return load_culture_data(filepath, 'plant_month', 'harvest_month', 12)

def load_culture_doys(filepath):
    """Extract cultivation day-of-years from the given filepath."""

    return load_culture_data(filepath, 'plant_date', 'harvest_date', 365)

def load_irweights(filepath, column, ircol='hierid'):
    df = pd.read_csv(files.sharedpath(filepath), index_col=ircol)

    weights = {}
    for index, row in df.iterrows():
        weights[index] = row[column]

    return weights

# Use partial_irweights in conjunction with get_file_cached
def partial_irweights(column, ircol='hierid'):
    return lambda filepath: load_irweights(filepath, column, ircol=ircol)

file_cache = {}

def get_file_cached(filepath, loader):
    if filepath not in file_cache:
        file_cache[filepath] = loader(filepath)

    return file_cache[filepath]

