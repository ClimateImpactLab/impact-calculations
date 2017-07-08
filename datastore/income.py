import csv
import numpy as np
from impactlab_tools.utils import files
from helpers import header
import population

gdppc_filepath = 'social/baselines/gdppc-merged.csv'
gdppc_baseline_filepath = 'social/baselines/gdppc-merged-baseline.csv' # only baseline values from gdppc_filepath

def baseline_future_collate(iter, endbaseline):
    baseline_values = {} # {region: [values]}
    future_years = {} # {region: {year: value}}

    for region, year, value in iter:
        if region not in baseline_values:
            baseline_values[region] = []
            future_years[region] = {}

        if year <= endbaseline:
            baseline_values[region].append(value)
        else:
            future_years[region][year] = value

    return baseline_values, future_years

def each_gdppc_fromfile(model, scenario, dependencies, filepath=None):
    if filepath is None:
        filepath = gdppc_filepath
    with open(files.sharedpath(filepath), 'r') as fp:
        reader = csv.reader(header.deparse(fp, dependencies))
        headrow = reader.next()

        for row in reader:
            if row[headrow.index('model')] != model or row[headrow.index('scenario')] != scenario:
                continue

            region = row[headrow.index('hierid')]
            year = int(row[headrow.index('year')])
            value = float(row[headrow.index('value')])

            yield region, year, value

def baseline_future_fromfile(model, scenario, endbaseline, dependencies):
    return baseline_future_collate(each_gdppc_fromfile(model, scenario, dependencies), endbaseline)

def each_gdppc_nightlight(model, scenario, dependencies, filepath=None):
    # Load all gdppc weights
    weights = {} # {hierid: weight}
    with open(files.sharedpath('social/baselines/nightlight_weight.csv'), 'r') as fp:
        reader = csv.reader(fp)
        headrow = reader.next()

        minover0 = 1.
        for row in reader:
            value = row[headrow.index('gdppc_ratio')]
            if value == '0':
                weights[row[headrow.index('hierid')]] = 'low'
            elif value == '':
                weights[row[headrow.index('hierid')]] = 1.
            else:
                weights[row[headrow.index('hierid')]] = float(value)
                if float(value) < minover0:
                    minover0 = float(value)

        for hierid in weights:
            if weights[hierid] == 'low':
                weights[hierid] = minover0

    for region, year, value in each_gdppc_fromfile(model, scenario, dependencies, filepath=filepath):
        yield region, year, value * weights.get(region, 1)

def baseline_future_gdppc_nightlight(model, scenario, endbaseline, dependencies):
    return baseline_future_collate(each_gdppc_nightlight(model, scenario, dependencies), endbaseline)

def each_country_gdp(model, scenario):
    with open(files.datapath("ssp_baseline_data/data/gdp.csv"), 'r') as fp:
        reader = csv.reader(fp)
        headrow = reader.next()

        for row in reader:
            if row[0] != model or row[1] != scenario:
                continue

            iso = row[2]
            for cc in range(headrow.index('2000'), headrow.index('2105')):
                value = row[cc]
                if value:
                    yield iso, int(headrow[cc]), float(value) * 1e9 # in billions

def baseline_future_country_gdp(model, scenario, endbaseline):
    return baseline_future_collate(each_country_gdp(model, scenario), endbaseline)

#### Nightlights

def load_nightlights():
    values = {} # {region: value}

    with open(files.sharedpath('social/baselines/nightlight_baseline.csv'), 'r') as fp:
        reader = csv.reader(fp)
        headrow = reader.next()

        for row in reader:
            values[row[headrow.index('hierid')]] = float(row[headrow.index('light_mean')])

    return values

# Return the GDPpc of each region within a country
def within_country_gdppc_weights(beta, nightlights, verbose=False):
    preweights = np.exp(beta * (np.log(nightlights) - np.mean(np.log(nightlights))))
    if verbose:
        print preweights[0:20]

    return preweights / np.sum(preweights)

def within_country_gdppc(gdp, pops, weights):
    return gdp * weights / pops

if __name__ == '__main__':
    dependencies = []

    beta = 0.28

    print "Read baselines and futures...."
    region_baseline, region_future = baseline_future_fromfile('IIASA GDP', 'SSP1_v9_130219', 2010, dependencies)
    country_baseline, country_future = baseline_future_country_gdp('IIASA GDP', 'SSP1_v9_130219', 2010)

    print "Read baselines..."
    pop_baseline = population.population_baseline_data(2000, 2010, dependencies)
    nightlights = load_nightlights()

    print "Aggregating..."
    # Collect all the countries
    allisos = {} # {ISO: [hierids]}
    for hierid in pop_baseline:
        iso = hierid[:3]
        if iso not in allisos:
            allisos[iso] = []

        allisos[iso].append(hierid)

    # Determine country-wide populations
    pop_baseline_country = {} # {ISO: totalpop}
    for iso in allisos:
        pop_baseline_country[iso] = np.sum([np.mean(pop_baseline[hierid].values()) for hierid in allisos[iso]])

    # Calculate the mean gdppc
    mean_gdppc = np.mean([np.mean(country_baseline[iso]) / pop_baseline_country[iso] for iso in country_baseline])

    print "Writing..."
    with open("baseline_gdppcest.csv", 'w') as fp:
        header.write(fp, "Baseline GDP per capita (2005 PPP) (SSPs)",
                     header.dated_version("GCP-GDPPC-SSP"), dependencies,
                     {'hierid': ("Hierarchy ID", 'str'),
                      'constant': ("Country constant GDP per capita", '2005 PPP USD'),
                      'storienight': ("Storiegard nightlights GDP per capita", '2005 PPP USD')},
                     description="Generated by datastore/income.py")
        writer = csv.writer(fp, lineterminator='\n')
        writer.writerow(['hierid', 'constant', 'storienight'])

        for iso in allisos:
            country_nightlights = [nightlights[hierid] for hierid in allisos[iso]]
            weights = within_country_gdppc_weights(beta, country_nightlights)

            country_pops = [np.mean(pop_baseline[hierid].values()) for hierid in allisos[iso]]
            if iso in country_baseline:
                country_gdp = np.mean(country_baseline[iso])
            else:
                country_gdp = mean_gdppc * sum(country_pops)

            gdppcs = within_country_gdppc(country_gdp, country_pops, weights)
            #if iso == 'USA':
            #    print np.mean(gdppcs)
            #    print sum(np.array(country_pops) * gdppcs) / sum(country_pops)

            for ii in range(len(allisos[iso])):
                hierid = allisos[iso][ii]
                if hierid not in region_baseline:
                    constant_gdppc = mean_gdppc
                else:
                    constant_gdppc = np.mean(region_baseline[hierid])
                writer.writerow([hierid, constant_gdppc, gdppcs[ii]])
