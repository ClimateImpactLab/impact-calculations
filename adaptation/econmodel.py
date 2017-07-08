import csv
import numpy as np
from impactlab_tools.utils import files
from helpers import header
from datastore import population, popdensity, income_smoothed

def iterate_econmodels():
    modelscenarios = set() # keep track of model-scenario pairs

    dependencies = []
    with open(files.sharedpath('social/baselines/gdppc-merged-baseline.csv'), 'r') as fp:
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
        self.income_model = DynamicIncomeSmoothed(model, scenario, dependencies)
        self.pop_future_years = {} # {hierid: {year: value}}
        self.densities = {}

    def baseline_values(self, maxbaseline):
        dependencies = []

        if self.income_model.current_year < maxbaseline:
            gdppc_baseline = self.income_model.current_income
        else:
            print "Warning: re-reading baseline income."
            gdppc_baseline = self.income_model.get_baseline_income(self.model, self.scenario, self.dependencies)

        for region, year, value in population.each_future_population(self.model, self.scenario, dependencies):
            if region not in self.pop_future_years:
                self.pop_future_years[region] = {}

            self.pop_future_years[region][year] = value

        pop_baseline = population.population_baseline_data(2000, 2010, dependencies)

        self.densities = popdensity.load_popop()

        # Iterate through pop_baseline, since it has all regions
        for region in pop_baseline.keys():
            yield dict(region=region, gdppcs=gdppc_baseline.get(region, None),
                       popop=self.densities.get(region, None))

    def baseline_prepared(self, maxbaseline, numeconyears, func):
        """
        Return a dictionary {region: {gdppcs: [gdppcs], popop: popop}
        """
        econ_predictors = {} # {region: {gdppcs: [gdppcs], popop: popop}
        allmeans_gdppcs = []
        allmeans_popop = []
        for econbaseline in self.baseline_values(maxbaseline): # baseline through maxbaseline
            region = econbaseline['region']
            gdppcs = econbaseline['gdppcs']
            popop = econbaseline['popop']
            if gdppcs is None or popop is None:
                if popop is not None:
                    popop = func([popop])
                if gdppcs is not None:
                    gdppcs = func(gdppcs[-numeconyears:])
                econ_predictors[region] = dict(gdppcs=gdppcs, popop=popop)
            else:
                allmeans_gdppcs.append(np.mean(gdppcs[-numeconyears:]))
                allmeans_popop.append(popop)
                econ_predictors[region] = dict(gdppcs=func(gdppcs[-numeconyears:]), popop=func([popop]))

        econ_predictors['mean'] = dict(gdppcs=np.mean(allmeans_gdppcs), popop=np.mean(allmeans_popop)) # don't use mean popop-- all should have
        for region in econ_predictors:
            if econ_predictors[region]['gdppcs'] is None:
                econ_predictors[region]['gdppcs'] = func([econ_predictors['mean']['gdppcs']])
            if econ_predictors[region]['popop'] is None:
                econ_predictors[region]['popop'] = func([econ_predictors['mean']['popop']])

        return econ_predictors

    def get_gdppc_year(self, region, year):
        return self.income_model.get_income(region, year)

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
