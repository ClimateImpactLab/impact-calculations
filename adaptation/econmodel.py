import csv
from helpers import files, header
from datastore import population, popdensity, income

def iterate_econmodels():
    modelscenarios = set() # keep track of model-scenario pairs

    dependencies = []
    with open(files.datapath('baselines/gdppc.csv'), 'r') as fp:
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
