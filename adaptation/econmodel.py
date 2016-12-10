import csv
import numpy as np
from helpers import files, header
from datastore import population, popdensity, income

def iterate_econmodels():
    modelscenarios = set() # keep track of model-scenario pairs

    dependencies = []
    with open(files.sharedpath('social/baselines/gdppc.csv'), 'r') as fp:
        reader = csv.reader(header.deparse(fp, dependencies))
        headrow = reader.next()

        for row in reader:
            model = row[headrow.index('model')]
            scenario = row[headrow.index('scenario')]
            if (model, scenario) not in modelscenarios:
                yield model, scenario, SSPEconomicModel(model, scenario, dependencies)
                modelscenarios.add((model, scenario))

class SSPEconomicModel(object):
    def __init__(self, model, scenario, dependencies):
        self.model = model
        self.scenario = scenario
        self.dependencies = dependencies
        self.gdppc_future_years = {} # {hierid: {year: value}}
        self.pop_future_years = {} # {hierid: {year: value}}
        self.densities = {}

    def baseline_values(self, maxbaseline):
        dependencies = []

        gdppc_baseline, self.gdppc_future_years = income.baseline_future_gdppc_nightlight(self.model, self.scenario, 2010, dependencies)

        for region, year, value in population.each_future_population(self.model, self.scenario, dependencies):
            if region not in self.pop_future_years:
                self.pop_future_years[region] = {}

            self.pop_future_years[region][year] = value

        pop_baseline = population.population_baseline_data(2000, 2010, dependencies)

        self.densities = popdensity.load_popop()

        # Iterate through pop_baseline, since it has all regions
        for region in pop_baseline.keys():
            yield region, gdppc_baseline.get(region, None), self.densities.get(region, None)

    def baseline_prepared(self, maxbaseline, numeconyears, func):
        econ_predictors = {} # {region: ([gdppcs], density)}
        allmeans_gdppcs = []
        allmeans_density = []
        for region, gdppcs, density in self.baseline_values(maxbaseline): # baseline through maxbaseline
            if gdppcs is None or density is None:
                if density is not None:
                    density = func([density])
                if gdppcs is not None:
                    gdppcs = func(gdppcs[-numeconyears:])
                econ_predictors[region] = [gdppcs, density]
            else:
                allmeans_gdppcs.append(np.mean(gdppcs[-numeconyears:]))
                allmeans_density.append(density)
                econ_predictors[region] = [func(gdppcs[-numeconyears:]), func([density])]

        econ_predictors['mean'] = [np.mean(allmeans_gdppcs), np.mean(allmeans_density)] # don't use mean density-- all should have
        for region in econ_predictors:
            if econ_predictors[region][0] is None:
                econ_predictors[region][0] = func([econ_predictors['mean'][0]])
            if econ_predictors[region][1] is None:
                econ_predictors[region][1] = func([econ_predictors['mean'][1]])

        return econ_predictors

    def get_gdppc_year(self, region, year):
        if region not in self.gdppc_future_years:
            return None

        if year in self.gdppc_future_years[region]:
            return self.gdppc_future_years[region][year]

        return None

    def get_popop_year(self, region, year):
        if region not in self.pop_future_years:
            if region in self.densities:
                return self.densities[region]
            else:
                return None
        elif region not in self.densities:
            return None

        if year in self.pop_future_years[region]:
            in2010 = self.pop_future_years[region][2010]
            if in2010 > 0:
                return self.pop_future_years[region][year] * self.densities[region] / self.pop_future_years[region][2010]

        return None
