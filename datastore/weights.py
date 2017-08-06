import pandas as pd
from impactlab_tools.utils import files
import population, agecohorts, spacetime

def interpret(config):
    assert 'weighting' in config
    if '/' in config['weighting']:
        df = pd.read_csv(files.configpath(config['weighting']))
        if 'model' in df:
            df = df[df.model == config['iam']]
        if 'scenario' in df:
            df = df[df.model == config['ssp']]
        regions = df['regions'].unique()
        return lambda year0, year1: spacetime.SpaceTimeLazyData(year0, year1, regions, lambda region: df[df.region == region]

    econ_model = config['iam']
    econ_scenario = config['ssp']

    if config['weighting'] == 'population':
        halfweight = population.SpaceTimeBipartiteData(1981, 2100, None)
        return lambda year0, year1: halfweight.load_population(year0, year1, econ_model, econ_scenario)

    if config['weighting'] in agecohorts.columns:
        halfweight = agecohorts.SpaceTimeBipartiteData(1981, 2100, None)
        return lambda year0, year1: halfweight.load_population(year0, year1, econ_model, econ_scenario, config['weighting'])

    raise ValueError("Unknown weighting.")
