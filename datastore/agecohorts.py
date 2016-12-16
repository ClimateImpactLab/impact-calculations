columns = ['age0-4', 'age5-64', 'age65+']

def load_agecohorts(model, scenario):
    data = {}

    agefile = file.sharedpath('social/baselines/cohort_population_aggr.csv')
    with open(agefile, 'r') as fp:
        reader = csv.reader(fp)
        header = map(lambda s: s.strip(), reader.next())
        for row in reader:
            if row[header.index('age0-4')].strip() == '' or row[header.index('age0-4')].strip() == '0':
                continue
            
            if row[header.index('MODEL')] == model and row[header.index('Scenario')] == scenario:
                region = row[header.index('REGION')]
                
                if region not in data:
                    data[region] = {}
                data[region][year] = [row[header.index(column)] for column in columns]

    return data

def load_ageshares(model, scenario):
    data = load_agecohorts(model, scenario)

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
