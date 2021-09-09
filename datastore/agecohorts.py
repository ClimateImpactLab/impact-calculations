"""Functions to access age cohort projection data.

We use three age groups: <5, called "young"; 5 - 64, called "older",
and >64, called "oldest". The portions of the population within each
of these age groups can be used as a weighting variable or a
covariate.

This data is derived from the SSP dataset, using the script
baselines/AgeGroupAggr.py in the socioeconomics repository:
https://bitbucket.org/ClimateImpactLab/socioeconomics/src/master/baselines/AgeGroupAggr.py

"""

import csv
import numpy as np
from impactlab_tools.utils import files
from helpers import header
from . import population, spacetime

# The three age groups; results returned in same order
columns = ['age0-4', 'age5-64', 'age65+']

def load_agecohorts(model, scenario):
    """Load the age cohort data for a given model and scenario.

    Parameters
    ----------
    model : str
        SSP model, such as "IIASA-WiC POP"
    scenario : str
        SSP scenario, such as "SSP3_v9_130115"

    Returns
    -------
    dict{str => dict{int => list}}
        A dictionary with a key for each ISO region; the value is a
        dictionary which maps years to a list of cohort portions.
    """
    data = {}

    agefile = files.sharedpath('social/baselines/cohort_population_aggr.csv')
    with open(agefile, 'r') as fp:
        reader = csv.reader(fp)
        header = [s.strip() for s in next(reader)] # drop extra whitespace
        for row in reader:
            row = [s.strip() for s in row]
            if row[header.index('age0-4')] == '' or float(row[header.index('age0-4')]) == 0:
                continue # row contains no data

            # Check if this corresponds to the requested model-scenario
            if (model is None or row[header.index('MODEL')] == model) and row[header.index('Scenario')][0:4] == scenario[0:4]:
                region = row[header.index('REGION')]

                # Fill in the data
                if region not in data:
                    data[region] = {}

                values = [float(row[header.index(column)]) for column in columns]

                data[region][int(row[header.index('YEAR')])] = values

    return data

def load_ageshares(model, scenario):
    data = load_agecohorts(model, scenario)
    if len(data) == 0:
        # Get data from another model
        data = load_agecohorts(None, scenario)

    sumbyyear = {}
    countbyyear = {}
    
    for region in data:
        for year in data[region]:
            pops = data[region][year]
            data[region][year] = np.array(pops) / sum(pops)

            if year not in sumbyyear:
                sumbyyear[year] = np.array(data[region][year])
                countbyyear[year] = 1
            else:
                sumbyyear[year] += data[region][year]
                countbyyear[year] += 1

    data['mean'] = {year: sumbyyear[year] / countbyyear[year] for year in sumbyyear}

    return data

def load_ageshares_allyears(year0, year1, model, scenario, column):
    data = load_ageshares(model, scenario)
    for region in data:
        alltime = np.zeros(year1 - year0 + 1)
        datastart = min(data[region].keys())
        assert year0 <= datastart, "Not designed to handle late-starting request" # there would be nothing in year-1 to copy!

        alltime[:(datastart - year0 + 1)] = data[region][datastart][columns.index(column)]
        for year in range(max(year0, datastart+1), year1+1):
            if year in  data[region]:
                alltime[year - year0] = data[region][year][columns.index(column)]
            else:
                alltime[year - year0] = alltime[year - year0 - 1]

        data[region] = alltime

    return data

def age_from_filename(filename):
    if '-young' in filename or '-kid' in filename:
        return 'age0-4'
    if '-older' in filename or '-person' in filename:
        return 'age5-64'
    if '-oldest' in filename or '-geezer' in filename:
        return 'age65+'
    if '-combined' in filename:
        return 'total'

    raise ValueError('Unknown age group in %s' % filename)

class SpaceTimeBipartiteData(spacetime.SpaceTimeBipartiteData):
    def __init__(self, year0, year1, regions):
        self.total_population = population.SpaceTimeBipartiteData(year0, year1, regions)
        self.dependencies = self.total_population.dependencies + ['cohort_population_aggr.csv']
        self.regions = self.total_population.regions
        
        super(SpaceTimeBipartiteData, self).__init__(year0, year1, self.regions)

    # Keep as load_population, to not conflat with load() which doesn't need age group
    def load(self, year0, year1, model, scenario, agegroup, shareonly=False):
        if shareonly and agegroup != 'total':
            ageshares = load_ageshares_allyears(year0, year1, model, scenario, agegroup)

            return spacetime.SpaceTimeLazyData(self.year0, self.year1, self.regions, lambda region: ageshares.get(region[:3], ageshares['mean']))
            
        stweight = self.total_population.load(year0, year1, model, scenario)

        if agegroup == 'total':
            return stweight
        
        ageshares = load_ageshares_allyears(year0, year1, model, scenario, agegroup)

        return spacetime.SpaceTimeLazyData(self.year0, self.year1, self.regions, lambda region: stweight.get_time(region) * ageshares.get(region[:3], ageshares['mean']))

if __name__ == '__main__':
    halfweight = SpaceTimeBipartiteData(2010, 2020, None)
    population = halfweight.load_population(2010, 2020, 'low', 'SSP5', 'age65+')
    print(population.get_time('BWA.4.13'))
    print(population.get_time('CAN.1.2.28'))
