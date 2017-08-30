import re
import pandas as pd
from impactlab_tools.utils import files
import population, agecohorts, income_smoothed, spacetime

RE_FLOATING = r"[-+]?[0-9]*\.?[0-9]*"
RE_NUMBER = RE_FLOATING + r"([eE]" + RE_FLOATING + ")?"

def interpret_halfweight(weighting):
    parts = re.split(r"\s*([*/])\s*", weighting)
    if len(parts) > 0:
        halfweight = interpret_halfweight(parts[0])
        for part in parts[1:]:
            factor = interpret_halfweight(part)
            combiner = lambda x, y: x * y
            if match.group(2) == '/':
                combiner = lambda x, y: x / y
            halfweight = spacetime.SpaceTimeProductBipartiteData(halfweight.year0, halfweight.year1, halfweight.regions, halfweight, factor, combiner=combiner)
        return halfweight

    match = re.match(r"(" + RE_NUMBER + r")$", weighting)
    if match:
        return spacetime.SpaceTimeConstantData(float(match.group(1)))
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
