import csv
import numpy as np
from impactlab_tools.utils import files
from impactcommon.exogenous_economy import provider, gdppc
from helpers import header
from datastore import population, popdensity

def iterate_econmodels(config={}):
    modelscenarios = set() # keep track of model-scenario pairs

    dependencies = []
    with open(files.sharedpath('social/baselines/gdppc-merged-baseline.csv'), 'r') as fp:
        reader = csv.reader(header.deparse(fp, dependencies))
        headrow = reader.next()

        for row in reader:
            model = row[headrow.index('model')]
            scenario = row[headrow.index('scenario')]
            if scenario == 'SSP5' and config.get('ssp', None) != 'SSP5':
                continue # Dropping entire scenario
            
            if (model, scenario) not in modelscenarios:
                yield model, scenario, SSPEconomicModel(model, scenario, dependencies, config)
                modelscenarios.add((model, scenario))

def get_economicmodel(only_scenario, only_model):
    for model, scenario, economicmodel in iterate_econmodels():
        if model == only_model and scenario == only_scenario:
            return economicmodel
                
class SSPEconomicModel(object):
    def __init__(self, model, scenario, dependencies, config):
        self.model = model
        self.scenario = scenario
        self.dependencies = dependencies
        self.income_model = provider.BySpaceTimeFromSpaceProvider(gdppc.GDPpcProvider(model, scenario))
        self.pop_future_years = {} # {hierid: {year: value}}
        self.densities = {}

    def reset(self):
        self.income_model.reset()

    def baseline_prepared(self, maxbaseline, numeconyears, func):
        """
        Return a dictionary {region: {loggdppc: loggdppc, popop: popop}
        """
        # Prepare population future
        for region, year, value in population.each_future_population(self.model, self.scenario, self.dependencies):
            if region not in self.pop_future_years:
                self.pop_future_years[region] = {}

            self.pop_future_years[region][year] = value

        # Prepare population baseline
        pop_baseline = population.population_baseline_data(2000, 2015, self.dependencies)

        # Prepare densitiy factor
        self.densities = popdensity.load_popop()
        mean_density = np.mean(self.densities.values())
        
        econ_predictors = {} # {region: {loggdppc: loggdppc, popop: popop}

        # Iterate through pop_baseline, since it has all regions
        for region in pop_baseline.keys():
            # Get the income timeseries
            gdppcs = self.income_model.get_timeseries(region)
            baseline_gdppcs = gdppcs[:maxbaseline - self.income_model.get_startyear() + 1]
            # Get the popop value
            popop = self.densities.get(region, mean_density)
            # Pass it into the func
            econ_predictors[region] = dict(loggdppc=func(np.log(baseline_gdppcs)), popop=func([popop]))
        
        return econ_predictors

    def get_loggdppc_year(self, region, year):
        gdppc = self.income_model.get_value(region, year)
        return np.log(gdppc)

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
