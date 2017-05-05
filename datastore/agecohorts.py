import csv
import numpy as np
from impactlab_tools.utils import files
from helpers import header

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
