import csv
import numpy as np
from impactlab_tools.utils import files
from helpers import header

cached_data = {} # id => (data, version)

def get_data(id, units):
    """
    Returns data, version.
    """
    if id in cached_data:
        return cached_data[id]

    if id == 'mortality-deathrates':
        assert units == 'deaths/person'

        #import mortality
        #return mortality.load_mortality_rates(), "CMF-1999-2010"

        dependencies = []
        with open(files.sharedpath("social/baselines/mortality-physical/combined.csv"), 'r') as fp:
            reader = csv.reader(header.deparse(fp, dependencies))
            headrow = next(reader)

            yearcol = headrow.index('year')
            regcol = headrow.index('hierid')
            valcol = headrow.index('value')

            yearvalues = {} # {region: [values]}
            for row in reader:
                year = int(row[yearcol])
                if year >= 2001 and year <= 2010:
                    if row[regcol] in yearvalues:
                        yearvalues[row[regcol]].append(float(row[valcol]))
                    else:
                        yearvalues[row[regcol]] = [float(row[valcol])]

            allmeans = []
            for region in yearvalues:
                regmean = np.mean(yearvalues[region])
                allmeans.append(regmean)
                yearvalues[region] = regmean

            yearvalues['mean'] = np.mean(allmeans)

            cached_data[id] = (yearvalues, dependencies[0])
            return cached_data[id]
