import numpy as np
import pandas as pd
from impactlab_tools.utils import files

def load_culture_months(filepath):
    df = pd.read_csv(files.sharedpath(filepath), index_col='hierid')

    culture_months = {}
    for index, row in df.iterrows():
        if not np.isnan(row['plant_month']) and not np.isnan(row['harvest_month']):
            plant = int(row['plant_month'])
            harvest = int(row['harvest_month'])
            if harvest < plant:
                harvest += 12
            culture_months[index] = plant, harvest

    return culture_months

def load_culture_doys(filepath):
    df = pd.read_csv(files.sharedpath(filepath), index_col='hierid')

    culture_dates = {}
    for index, row in df.iterrows():
        if not np.isnan(row['plant_date']) and not np.isnan(row['harvest_date']):
            plant = int(row['plant_date'])
            harvest = int(row['harvest_date'])
            if harvest < plant:
                harvest += 12
            culture_dates[index] = plant, harvest

    return culture_dates

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

