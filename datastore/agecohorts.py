import csv
import numpy as np
from impactlab_tools.utils import files
from helpers import header
import population, spacetime

columns = ['age0-4', 'age5-64', 'age65+']

def load_agecohorts(model, scenario):
    data = {}

    agefile = files.sharedpath('social/baselines/cohort_population_aggr.csv')
    with open(agefile, 'r') as fp:
        reader = csv.reader(fp)
        header = map(lambda s: s.strip(), reader.next())
        for row in reader:
            row = map(lambda s: s.strip(), row)
            if row[header.index('age0-4')] == '' or float(row[header.index('age0-4')]) == 0:
                continue
            
            if (model is None or row[header.index('MODEL')] == model) and row[header.index('Scenario')][0:4] == scenario[0:4]:
                region = row[header.index('REGION')]
                
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
                sumbyyear[year] = data[region][year]
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

    raise ValueError('Unknown age group')

class SpaceTimeBipartiteData(spacetime.SpaceTimeData):
    def __init__(self, year0, year1, regions):
        self.total_population = population.SpaceTimeBipartiteData(year0, year1, regions)
        self.dependencies = self.total_population.dependencies + ['cohort_population_aggr.csv']

        super(SpaceTimeBipartiteData, self).__init__(year0, year1, self.total_population.regions)
        
    def load_population(self, year0, year1, model, scenario, agegroup):
        stweight = self.total_population.load_population(year0, year1, model, scenario)
        ageshares = load_ageshares_allyears(year0, year1, model, scenario, agegroup)

        return spacetime.SpaceTimeLazyData(self.year0, self.year1, self.regions, lambda region: stweight.get_time(region) * ageshares.get(region, ageshares['mean']))


