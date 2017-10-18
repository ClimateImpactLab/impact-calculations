import os
import pandas as pd
import metacsv
from impactlab_tools.utils import files

def get_cached(key, scenario, model, onmiss):
    path = files.sharedpath('scratch/forecastcache/' + key)
    if not os.path.exists(path):
        os.makedirs(path, 0775)

    filepath = os.path.join(path, scenario + '-' + model + '.csv')
    if os.path.exists(filepath):
        return metacsv.read_csv(filepath)

    df, attrs, coords, variables = onmiss(key, scenario, model)
    metacsv_df = metacsv.DataFrame(df, attrs=attrs, coords=coords, variables=variables)
    metacsv_df.to_csv(filepath)
    os.chmod(filepath, 0664) # RW, RW, R

    return metacsv_df

def get_cached_byregion(key, scenario, model, onmiss, variables, attrs):
    def onmiss_metacsv(key, scenario, model):
        dicts = onmiss(key, scenario, model)
        if isinstance(dicts, tuple):
            assert len(dicts) == len(variables)
        else:
            dicts = [dicts]
            
        regions = dicts[0].keys()
        data = {variable: [] for variable in variables}
        for region in regions:
            for ii in range(len(dicts)):
                data[variables.keys()[ii]].append(dicts[ii][region])

        data['region'] = regions
                
        return pd.DataFrame(data), attrs, ['region'], variables

    df = get_cached(key, scenario, model, onmiss_metacsv)
    regions = df.index.values
    
    dicts = []
    for variable in variables:
        data = df[variable]
        dicts.append({regions[ii]: data[ii] for ii in range(len(regions))})

    return tuple(dicts)
