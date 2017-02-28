import csv, os
import numpy as np
from helpers import files, header
import spacetime

use_merged = True

def each_future_population(model, scenario, dependencies):
    # Try to load an model-specific file
    if use_merged:
        populationfile = files.sharedpath('social/baselines/population/merged/population-merged.' + scenario + '.csv')
        rowchecks = lambda row, headrow: True
    else:
        populationfile = files.sharedpath('social/baselines/population/future/population-future.' + model + '.' + scenario + '.csv')
        if os.path.exists(populationfile):
            rowchecks = lambda row, headrow: True
        else:
            print "Cannot find model-specific populations."
            populationfile = files.sharedpath('social/baselines/population/future/population-future.csv')
            rowchecks = lambda row, headrow: row[headrow.index('model')] == model and row[headrow.index('scenario')] == scenario

    with open(populationfile, 'r') as fp:
        reader = csv.reader(header.deparse(fp, dependencies))
        headrow = reader.next()

        for row in reader:
            if not rowchecks(row, headrow):
                continue

            try:
                region = row[headrow.index('region')]
                year = int(row[headrow.index('year')])
                value = float(row[headrow.index('value')])
            except Exception as e:
                print "Could not get all values for row from %s:" % populationfile
                print headrow
                print row
                raise e

            yield region, year, value

def population_baseline_data(year0, year1, dependencies):
    baselinedata = {} # {region: {year: value}}
    with open(files.sharedpath("social/weightlines/population.csv"), 'r') as fp:
        reader = csv.reader(header.deparse(fp, dependencies))
        headrow = reader.next()

        for row in reader:
            region = row[headrow.index('region')]
            year = int(row[headrow.index('year')])
            if year < year0 or year > year1:
                continue

            value = float(row[headrow.index('value')])

            if region not in baselinedata:
                baselinedata[region] = {}
            baselinedata[region][year] = value

    return baselinedata

def extend_population_future(baselinedata, year0, year1, regions, model, scenario, dependencies):
    popout = np.ones((year1 - year0 + 1, len(regions))) * np.nan

    # Fill in the values
    for ii in range(len(regions)):
        subset = baselinedata[regions[ii]]
        for year in subset:
            if year < year0 or year > year1:
                continue
            popout[year - year0, ii] = subset[year]

    for region, year, value in each_future_population(model, scenario, dependencies):
        if year < year0 or year > year1:
            continue
        ii = regions.index(region)
        popout[year - year0, ii] = value

    # Interpolate values by holding constant
    for ii in range(len(regions)):
        givens = np.flatnonzero(np.isfinite(popout[:, ii]))
        starts = [0] + givens[1:].tolist()
        ends = givens[1:].tolist() + [year1 - year0 + 1]
        for jj in range(len(givens)):
            popout[starts[jj]:ends[jj], ii] = popout[givens[jj], ii]

    return popout

def read_population_allyears(year0, year1, regions, model, scenario, dependencies):
    """Return an array of populations YEARS x REGIONS.
    regions may be None, in which case they are taken from the baseline data."""

    baselinedata = population_baseline_data(year0, year1, dependencies)

    if regions is None:
        regions = baselinedata.keys()

    return extend_population_future(baselinedata, year0, year1, regions, model, scenario, dependencies)

class SpaceTimeBipartiteData(spacetime.SpaceTimeData):
    def __init__(self, year0, year1, regions):
        self.dependencies = []

        # Load the baseline data
        self.baselinedata = population_baseline_data(year0, year1, self.dependencies)

        if regions is None:
            regions = self.baselinedata.keys()

        super(SpaceTimeBipartiteData, self).__init__(year0, year1, regions)

    def load_population(self, year0, year1, model, scenario):
        popout = extend_population_future(self.baselinedata, year0, year1, self.regions,
                                          model, scenario, self.dependencies)
        return spacetime.SpaceTimeLoadedData(self.year0, self.year1, self.regions, popout)
