"""System for providing socioeconomic scenario information.

Socioeconomic scenario information is drawn from the SSPs. There are
multiple SSPs (generally 5) and multiple models (generally 2) can
produce each one. As with GCMs, we discover these scenarios and then
provide an iterator to an SSPEconomicModel object, which is the
clearinghouse for their content.
"""

import csv
import numpy as np
from impactlab_tools.utils import files
from impactcommon.exogenous_economy import provider, gdppc
from helpers import header
from datastore import population, popdensity

extra_econmodels = {} # Filled in later

def iterate_econmodels(config=None):
    """Discover and yield each known scenario as a SSPEconomicModel.
    
    Parameters
    ----------
    config : dict (optional)
        Configuration dictionary with filtering information.

    Yields
    ------
    tuple of str, str, SSPEconomicModel
        The first str is the model producing the data; the second is the scenario.
    """
    if config is None:
        config = {}
    modelscenarios = set() # keep track of model-scenario pairs
    
    dependencies = []
    # Look for scenarios in the GDPpc baseline data
    with open(files.sharedpath('social/baselines/gdppc-merged-baseline.csv'), 'r') as fp:
        reader = csv.reader(header.deparse(fp, dependencies))
        headrow = next(reader)

        for row in reader:
            model = row[headrow.index('model')]
            scenario = row[headrow.index('scenario')]

            # Yield each newly discovered model, scenario combination
            if (model, scenario) not in modelscenarios:
                yield model, scenario, SSPEconomicModel(model, scenario, dependencies, config)
                modelscenarios.add((model, scenario))

def get_economicmodel(only_scenario, only_model):
    for model, scenario, economicmodel in iterate_econmodels():
        if model == only_model and scenario == only_scenario:
            return economicmodel

def check_extra_economicmodel(only_scenario, only_model):
    if (only_model, only_scenario) in extra_econmodels:
        return extra_econmodels[(only_model, only_scenario)]
    return None

def compare_scenario(obs, desired):
    if isinstance(obs, int):
        return obs == desired
    else:
        return obs[:4] in desired

class SSPEconomicModel(object):
    def __init__(self, model, scenario, dependencies, config):
        self.model = model
        self.scenario = scenario
        self.dependencies = dependencies
        self.income_model = provider.BySpaceTimeFromSpaceProvider(gdppc.GDPpcProvider(model, scenario))
        self.pop_future_years = {} # {hierid: {year: value}}
        self.densities = {}
        self.endbaseline = config.get('endbaseline', 2015)

    def reset(self):
        self.income_model.reset()

    def baseline_prepared(self, maxbaseline, numeconyears, func, country_level_gdppc=False):
        """
        Return a dictionary {region: {loggdppc: loggdppc, popop: popop}
        """
        # Prepare population future
        for region, year, value in population.each_future_population(self.model, self.scenario, self.dependencies):
            if region not in self.pop_future_years:
                self.pop_future_years[region] = {}

            self.pop_future_years[region][year] = value

        # Prepare population baseline
        pop_baseline = population.population_baseline_data(2000, self.endbaseline, self.dependencies)

        # Prepare densitiy factor
        self.densities = popdensity.load_popop()
        mean_density = np.mean(list(self.densities.values()))
        
        econ_predictors = {} # {region: {loggdppc: loggdppc, popop: popop}

        # Iterate through pop_baseline, since it has all regions
        for region in list(pop_baseline.keys()):
            query_region = str(region.split(".")[0]) if country_level_gdppc else region
            
            # Get the income timeseries
            gdppcs = self.income_model.get_timeseries(query_region)
            if maxbaseline < self.income_model.get_startyear():
                baseline_gdppcs = [gdppcs[0]]
            else:
                baseline_gdppcs = gdppcs[:maxbaseline - self.income_model.get_startyear()]
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

    def get_population_year(self, region, year):
        if region not in self.pop_future_years:
            return np.nan
        if year not in self.pop_future_years[region]:
            return np.nan
        return self.pop_future_years[region][year]
    
class RFFEconomicModel(object):
    def __init__(self, model, scenario, dependencies, config):
        self.model = model
        self.scenario = scenario
        self.dependencies = dependencies
        gdppcprovider = gdppc.read_hierarchicalgdppcprovider(model, scenario,
                                                             "social/rff/gdppc-growth-%d.csv" % scenario,
                                                             "social/rff/gdppc-nohier-%d.csv" % scenario,
                                                             'social/baselines/nightlight_weight_normalized.csv',
                                                             use_sharedpath=True,
                                                             startyear=2010, stopyear=2100)
        self.income_model = provider.BySpaceTimeFromSpaceProvider(gdppcprovider)
        self.endbaseline = config.get('endbaseline', 2015)

    def reset(self):
        self.income_model.reset()

    def baseline_prepared(self, maxbaseline, numeconyears, func, country_level_gdppc=False):
        """
        Return a dictionary {region: {loggdppc: loggdppc}}
        """
        # Prepare population baseline
        pop_baseline = population.population_baseline_data(2000, self.endbaseline, self.dependencies)

        econ_predictors = {} # {region: {loggdppc: loggdppc}}

        # Iterate through pop_baseline, since it has all regions
        for region in list(pop_baseline.keys()):
            query_region = str(region.split(".")[0]) if country_level_gdppc else region
            
            # Get the income timeseries
            gdppcs = self.income_model.get_timeseries(query_region)
            if maxbaseline < self.income_model.get_startyear():
                baseline_gdppcs = [gdppcs[0]]
            else:
                baseline_gdppcs = gdppcs[:maxbaseline - self.income_model.get_startyear()]
            # Pass it into the func
            econ_predictors[region] = dict(loggdppc=func(np.log(baseline_gdppcs)), popop=func([np.nan]))
        
        return econ_predictors

    def get_loggdppc_year(self, region, year):
        gdppc = self.income_model.get_value(region, year)
        return np.log(gdppc)

    def get_popop_year(self, region, year):
        return None

    def get_population_year(self, region, year):
        return np.nan

# Offer as extra model
extra_econmodels[('rff', 6546)] = RFFEconomicModel
