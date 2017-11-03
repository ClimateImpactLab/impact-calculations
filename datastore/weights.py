import re
import pandas as pd
from impactlab_tools.utils import files
import population, agecohorts, income_smoothed, spacetime

RE_FLOATING = r"[-+]?[0-9]*\.?[0-9]*"
RE_NUMBER = RE_FLOATING + r"([eE]" + RE_FLOATING + ")?"

def interpret_halfweight(weighting):
    parts = re.split(r"\s*([*/])\s*", weighting)
    if len(parts) > 1:
        halfweight = interpret_halfweight(parts[0])
        for ii in range(2, len(parts), 2):
            factor = interpret_halfweight(parts[ii])
            combiner = lambda x, y: x * y
            if parts[ii-1] == '/':
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

    return interpret_halfweight(config['weighting'])

def get_weight_args(config):
    econ_model = config['iam']
    econ_scenario = config['ssp']

    args = [econ_model, econ_scenario]
    
    if config['weighting'] in agecohorts.columns:
        args.append(config['weighting'])

    return tuple(args)

if __name__ == '__main__':
    import sys, csv
    import irregions

    dependencies = []
    regions = irregions.load_regions("hierarchy.csv", dependencies)
    
    weighting = sys.argv[1]
    halfweight = interpret_halfweight(weighting)
    stweight = halfweight.load(1981, 2100, sys.argv[2], sys.argv[3])

    writer = csv.writer(sys.stdout)
    writer.writerow(['region', 'year', 'weight'])
    for region in regions:
        weights = stweight.get_time(region)
        for year in range(1981, 2101):
            writer.writerow([region, year, weights[year - 1981]])
