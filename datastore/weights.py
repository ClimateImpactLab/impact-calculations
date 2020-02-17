"""
Functions for intrepretting weighting configuration options, for use with aggregator.py.
See docs/aggregator.md for more details.
"""

import re, os
import numpy as np
import pandas as pd
from impactlab_tools.utils import files
from impactcommon.exogenous_economy import gdppc
import population, agecohorts, spacetime, irregions

## Regular expressions to interpret configuration options
RE_FLOATING = r"[-+]?[0-9]*\.?[0-9]*" # matches floating point numbers, like 3.14
RE_NUMBER = RE_FLOATING + r"([eE]" + RE_FLOATING + ")?" # matches e-notation numbers, like 3.14e-3
RE_CSVNAME = r"[-\w./()]+" # intended to match either a filepath, like /path/weights.csv, or a CSV column name

## Weighting information files need column information as well, provided by the one of the syntaxes:
# Region-specific constants: constcsv/[filepath.csv]:[region column]:[weight column]
RE_CONSTFILE = r"constcsv/(%s?):(%s?):(%s?)(\s|$)" % (RE_CSVNAME, RE_CSVNAME, RE_CSVNAME)
# Annually varying weights: [filepath.csv]:[region column]:[year column]:[weight column]
RE_YEARLYFILE = r"(%s?):(%s?):(%s?):(%s?)(\s|$)" % (RE_CSVNAME, RE_CSVNAME, RE_CSVNAME, RE_CSVNAME)

def read_byext(filepath):
    """Reads a weighting data file, interpretting the format based on the extension.

    Parameters
    ----------
    filepath : str
        Path to a file that can be interpretted as a DataFrame.

    Returns
    -------
    pandas.DataFrame
        The contents of the file.
    """
    extension = os.path.splitext(filepath)[1].lower()
    assert extension in ['.csv', '.dta'] # we only handle these so far

    if extension == '.csv':
        return pd.read_csv(filepath)
    if extension == '.dta':
        return pd.read_stata(filepath)

# Singleton to describe weights that sum to 1.
HALFWEIGHT_SUMTO1 = "Sum to 1"

def interpret_halfweight(weighting):
    """Interpret the text of a configuration weighting scheme.

    Parameters
    ----------
    weighting : str
        A weighting description. See docs/aggregator.md for allowed options.

    Returns
    -------
    spacetime.SpaceTimeData
        Must have a valid `load` function, producing an object on which `get_time` can be called.
        
    """
    if weighting.lower() == 'sum-to-1':
        return HALFWEIGHT_SUMTO1
    
    match = re.match(RE_CONSTFILE, weighting)
    if match:
        df = read_byext(files.configpath(match.group(1)))
        regions = df[match.group(2)]

        submatch = re.match(r"sum\((%s?)\)" % RE_CSVNAME, match.group(3))
        if submatch:
            values = df.groupby([match.group(2)])[submatch.group(1)].sum()
            regions = list(values.index)
            mapping = {regions[ii]: values[ii] for ii in range(len(regions))}
            return spacetime.SpaceTimeSpatialOnlyData(mapping)

        values = df[match.group(3)]
        mapping = {regions[ii]: values[ii] for ii in range(len(regions))}
        return spacetime.SpaceTimeSpatialOnlyData(mapping)

    match = re.match(RE_YEARLYFILE, weighting)
    if match:
        df = read_byext(files.configpath(match.group(1)))
        regions = np.unique(df[match.group(2)])
        year0 = np.min(df[match.group(3)])
        year1 = np.max(df[match.group(3)])
        array = np.zeros((year1 - year0 + 1, len(regions)))
        indices = {regions[ii]: ii for ii in range(len(regions))}

        for index, row in df.iterrows():
            ii = indices[row[match.group(2)]]
            tt = row[match.group(3)] - year0
            array[tt, ii] = row[match.group(4)]
        
        return spacetime.SpaceTimeMatrixData(year0, year1, regions, array, ifmissing='mean', adm3fallback=True)

    parts = re.split(r"\s+([*/])\s+", weighting)
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
        return spacetime.SpaceTimeBipartiteFromProviderData(gdppc.GDPpcProvider, 2000, 2100, None)
    if weighting == 'area':
        dependencies = []
        areas = irregions.load_region_attr("regions/region-attributes-geom.csv", "hierid", "area", dependencies)
        return spacetime.SpaceTimeSpatialOnlyData(areas)

    raise ValueError("Unknown weighting.")

def interpret(config):
    assert 'weighting' in config
    if '/' in config['weighting'] and os.path.exists(files.configpath(config['weighting'])):
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
    stweight = halfweight.load(1981, 2100, sys.argv[2] if len(sys.argv) > 2 else None, sys.argv[3] if len(sys.argv) > 3 else None)

    writer = csv.writer(sys.stdout)
    writer.writerow(['region', 'year', 'weight'])
    for region in regions:
        weights = stweight.get_time(region)
        if isinstance(weights, float):
            writer.writerow([region, "all", weights])
        else:
            for year in range(1981, 2101):
                writer.writerow([region, year, weights[year - 1981]])
