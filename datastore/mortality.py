import csv, os
from helpers import files

"""agename is one of 0-0, 1-44, 45-64, 65-inf"""
age_group_mapping = {'0-0': ["< 1 year"], '1-44': ["1-4 years", "5-9 years", "10-14 years", "15-19 years", "20-24 years", "25-34 years", "35-44 years"], '45-64': ["45-54 years", "55-64 years"], '65-inf': ["65-74 years", "75-84 years", "85+ years"]}

def load_mortality_rates():
    scales = {}
    with open(files.datapath("mortality/cmf-1999-2010.txt")) as countyfp:
        reader = csv.reader(countyfp, delimiter='\t')
        reader.next() # skip header

        total_numer = 0
        total_denom = 0
        for row in reader:
            if len(row) < 5:
                continue
            numer = float(row[3])
            denom = float(row[4])
            total_numer += numer
            total_denom += denom
            scales[row[2]] = numer / denom

        scales['mean'] = total_numer / total_denom

        return scales

def load_mortality_age_rates(agename):
    scales = load_mortality_rates()
    groups = age_group_mapping[agename]

    scales_numer = {}
    scales_denom = {}
    with open(files.datapath("mortality/cmf-age-1999-2010.txt")) as countyfp:
        reader = csv.reader(countyfp, delimiter='\t')
        reader.next() # skip header

        total_numer = 0
        total_denom = 0
        for row in reader:
            if len(row) < 5 or row[1] not in groups:
                continue
            numer = float(row[5])
            denom = float(row[6])
            total_numer += numer
            total_denom += denom
            scales_numer[row[4]] = scales_numer.get(row[4], 0) + numer
            scales_denom[row[4]] = scales_denom.get(row[4], 0) + denom

    for fips in scales:
        if fips in scales_numer and fips in scales_denom:
            scales[fips] = scales_numer[fips] / scales_denom[fips]

    scales['mean'] = total_numer / total_denom

    return scales

def load_age_populations(agename, total_populations=None):
    groups = age_group_mapping[agename]

    populations = {}
    with open(files.datapath("mortality/cmf-age-1999-2010.txt")) as countyfp:
        reader = csv.reader(countyfp, delimiter='\t')
        reader.next() # skip header

        for row in reader:
            if len(row) < 5 or row[1] not in groups:
                continue
            population = float(row[6])
            populations[row[4]] = populations.get(row[4], 0) + population / 12.0

    # Fill in using age_population / total_population where unavailable
    if total_populations is not None:
        rate_numer = 0
        rate_denom = 0
        for fips in populations:
            if fips in total_populations:
                rate_numer += populations[fips]
                rate_denom += total_populations[fips]

        rate = float(rate_numer) / rate_denom

        for fips in total_populations:
            if fips not in populations:
                populations[fips] = rate * total_populations[fips]

    return populations

if __name__ == '__main__':
    for group in age_group_mapping:
        print group, load_mortality_age_rates(group)['mean']
