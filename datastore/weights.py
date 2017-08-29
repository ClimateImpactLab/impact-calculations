import re
import pandas as pd
from impactlab_tools.utils import files
import population, agecohorts, income_smoothed, spacetime

RE_FLOATING = r"[-+]?[0-9]*\.?[0-9]*"
RE_NUMBER = RE_FLOATING + r"([eE]" + RE_FLOATING + ")?"

def interpret_halfweight(weighting):
    match = re.match(r"(\S+?)\s*([*/])\s*(" + RE_NUMBER + r")$", weighting)
    if match:
        source = interpret_halfweight(match.group(1))
        factor = float(match.group(3))
        if match.group(2) == '/':
            factor = 1 / factor
        return spacetime.SpaceTimeProductBipartiteData(source.year0, source.year1, source.regions, source, factor)
            
    if weighting == 'population':
        return population.SpaceTimeBipartiteData(1981, 2100, None)
    if weighting in ['agecohorts'] + agecohorts.columns:
        return agecohorts.SpaceTimeBipartiteData(1981, 2100, None)
    if weighting == 'income':
        return income_smoothed.SpaceTimeBipartiteData(2000, 2100, None)

    raise ValueError("Unknown weighting.")

def interpret(config):
    assert 'weighting' in config
    if '/' in config['weighting']:
        df = pd.read_csv(files.configpath(config['weighting']))
        if 'model' in df:
            df = df[df.model == config['iam']]
        if 'scenario' in df:
            df = df[df.model == config['ssp']]
        regions = df['regions'].unique()
        return lambda year0, year1: spacetime.SpaceTimeLazyData(year0, year1, regions, lambda region: df[df.region == region])

    econ_model = config['iam']
    econ_scenario = config['ssp']

    if config['weighting'] == 'population':
        halfweight = population.SpaceTimeBipartiteData(1981, 2100, None)
        return lambda year0, year1: halfweight.load_population(year0, year1, econ_model, econ_scenario)

    if config['weighting'] in agecohorts.columns:
        halfweight = agecohorts.SpaceTimeBipartiteData(1981, 2100, None)
        return lambda year0, year1: halfweight.load_population(year0, year1, econ_model, econ_scenario, config['weighting'])

    raise ValueError("Unknown weighting.")
