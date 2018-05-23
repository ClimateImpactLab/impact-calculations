import csv
import numpy as np
from impactlab_tools.utils import files
from helpers import header
from datastore import population, popdensity, income_smoothed

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
                yield model, scenario, SSPEconomicModel(model, scenario, dependencies)
                modelscenarios.add((model, scenario))

def get_economicmodel(only_scenario, only_model):
    for model, scenario, economicmodel in iterate_econmodels():
        if model == only_model and scenario == only_scenario:
            return economicmodel
                
class SSPEconomicModel(object):
    def __init__(self, model, scenario, dependencies):
        self.model = model
        self.scenario = scenario
        self.dependencies = dependencies
        self.income_model = income_smoothed.DynamicIncomeSmoothed(model, scenario, dependencies)
        self.pop_future_years = {} # {hierid: {year: value}}
        self.densities = {}

    def reset(self):
        self.income_model.reset(self.dependencies)
        
    def baseline_values(self, maxbaseline):
        dependencies = []

        if self.income_model.current_year < maxbaseline:
            loggdppc_baseline = {region: np.log(self.income_model.current_income[region]) for region in self.income_model.current_income}
        else:
            print "Warning: re-reading baseline income."
            gdppcdata = self.income_model.get_baseline_income(self.model, self.scenario, self.dependencies)
            loggdppc_baseline = {region: np.log(gdppcdata[region]) for region in gdppcdata}

        for region, year, value in population.each_future_population(self.model, self.scenario, dependencies):
            if region not in self.pop_future_years:
                self.pop_future_years[region] = {}

            self.pop_future_years[region][year] = value

        pop_baseline = population.population_baseline_data(2000, 2010, dependencies)

        self.densities = popdensity.load_popop()

        # Iterate through pop_baseline, since it has all regions
        for region in pop_baseline.keys():
            yield dict(region=region, loggdppc=loggdppc_baseline.get(region, None),
                       popop=self.densities.get(region, None))

    def baseline_prepared(self, maxbaseline, numeconyears, func):
        """
        Return a dictionary {region: {loggdppc: loggdppc, popop: popop}
        """
        econ_predictors = {} # {region: {loggdppc: loggdppc, popop: popop}
        allmeans_loggdppc = []
        allmeans_popop = []
        for econbaseline in self.baseline_values(maxbaseline): # baseline through maxbaseline
            region = econbaseline['region']
            loggdppc = econbaseline['loggdppc']
            popop = econbaseline['popop']
            if loggdppc is None or popop is None:
                if popop is not None:
                    popop = func([popop])
                if loggdppc is not None:
                    loggdppc = func([loggdppc])
                econ_predictors[region] = dict(loggdppc=loggdppc, popop=popop)
            else:
                allmeans_loggdppc.append(loggdppc)
                allmeans_popop.append(popop)
                econ_predictors[region] = dict(loggdppc=func([loggdppc]), popop=func([popop]))

        econ_predictors['mean'] = dict(loggdppc=np.mean(allmeans_loggdppc), popop=np.mean(allmeans_popop)) # don't use mean popop-- all should have
        for region in econ_predictors:
            if econ_predictors[region]['loggdppc'] is None:
                econ_predictors[region]['loggdppc'] = func([econ_predictors['mean']['loggdppc']])
            if econ_predictors[region]['popop'] is None:
                econ_predictors[region]['popop'] = func([econ_predictors['mean']['popop']])

        return econ_predictors

    def get_loggdppc_year(self, region, year):
        gdppc = self.income_model.get_income(region, year)
        if gdppc is None:
            return None
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

    def get_population_year(self, region, year):
        if region not in self.pop_future_years:
            return np.nan
        if year not in self.pop_future_years[region]:
            return np.nan
        return self.pop_future_years[region][year]
    
