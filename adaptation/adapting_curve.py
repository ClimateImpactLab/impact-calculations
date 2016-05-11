import copy, csv, os
import numpy as np
from datastore import population, income, popdensity
from helpers import files, header
from openest.models.curve import StepCurve, AdaptableCurve

## Management of rolling means
## Rolling mean is [SUM, COUNT]

def rm_init(values):
    return [sum(values), len(values)]

def rm_add(rm, value, maxvalues):
    assert rm[1] <= maxvalues

    if rm[1] >= maxvalues:
        rm[0] = (maxvalues - 1) * rm[0] / rm[1] + value
        if rm[1] > maxvalues:
            rm[1] = maxvalues
    else:
        rm[0] += value
        rm[1] += 1

def rm_mean(rm):
    return rm[0] / rm[1]

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

## Currently just does Avg. Temp
class TemperatureIncomePredictorator(object):
    def __init__(self, weatherbundle, economicmodel, numtempyears, numeconyears, maxbaseline):
        self.numtempyears = numtempyears
        self.numeconyears = numeconyears

        print "Collecting baseline information..."
        temp_predictors = {}
        for region, temps in weatherbundle.baseline_values(maxbaseline): # baseline through maxbaseline
            temp_predictors[region] = temps[-numtempyears:]

        self.temp_predictors = temp_predictors

        gdppc_predictors = {}
        allmeans = []
        for region, gdppcs, density in economicmodel.baseline_values(maxbaseline): # baseline through maxbaseline
            allmeans.append(np.mean(gdppcs[-numeconyears:]))
            gdppc_predictors[region] = gdppcs[-numeconyears:]

        gdppc_predictors['mean'] = np.mean(allmeans)

        self.gdppc_predictors = gdppc_predictors

        self.economicmodel = economicmodel

    def get_baseline(self, region):
        gdppcs = self.gdppc_predictors.get(region, None)
        if gdppcs is None:
            gdppcs = self.gdppc_predictors['mean']
        return ((np.mean(self.temp_predictors[region]), np.mean(gdppcs)),)

    def get_update(self, region, year, temps):
        assert len(self.temp_predictors[region]) <= self.numtempyears

        if len(self.temp_predictors[region]) == self.numtempyears:
            self.temp_predictors[region] = self.temp_predictors[region][1:] + [np.mean(temps)]
        else:
            self.temp_predictors[region] = self.temp_predictors[region] + [np.mean(temps)]

        if region not in self.gdppc_predictors: # Keep baseline mean-of-means
            return ((np.mean(self.temp_predictors[region]), self.gdppc_predictors['mean']),)

        assert len(self.gdppc_predictors[region]) <= self.numeconyears

        gdppc = self.economicmodel.get_gdppc_year(region, year)
        if gdppc is not None:
            if len(self.gdppc_predictors[region]) == self.numeconyears:
                self.gdppc_predictors[region] = self.gdppc_predictors[region][1:] + [gdppc]
            else:
                self.gdppc_predictors[region] = self.gdppc_predictors[region] + [gdppc]

        return ((np.mean(self.temp_predictors[region]), np.mean(self.gdppc_predictors[region])),)

class BinsIncomeDensityPredictorator(object):
    def __init__(self, weatherbundle, economicmodel, binlimits, dropbin, numtempyears, numeconyears, maxbaseline):
        self.binlimits = binlimits
        self.dropbin = dropbin
        self.numtempyears = numtempyears
        self.numeconyears = numeconyears

        print "Collecting baseline information..."
        temp_predictors = {} # {region: [rm-bin-1, ...]}
        for region, binyears in weatherbundle.baseline_bin_values(binlimits, maxbaseline): # baseline through maxbaseline
            usedbinyears = []
            for ii in range(len(binyears)):
                if ii == dropbin:
                    continue
                usedbinyears.append(rm_init(binyears[ii][-numtempyears:]))
            temp_predictors[region] = usedbinyears

        self.temp_predictors = temp_predictors

        econ_predictors = {} # {region: ([gdppcs], density)}
        allmeans_gdppcs = []
        allmeans_density = []
        for region, gdppcs, density in economicmodel.baseline_values(maxbaseline): # baseline through maxbaseline
            if gdppcs is None or density is None:
                if density is not None:
                    density = rm_init([density])
                if gdppcs is not None:
                    gdppcs = rm_init(gdppcs[-numeconyears:])
                econ_predictors[region] = [gdppcs, density]
            else:
                allmeans_gdppcs.append(np.mean(gdppcs[-numeconyears:]))
                allmeans_density.append(density)
                econ_predictors[region] = [rm_init(gdppcs[-numeconyears:]), rm_init([density])]

        econ_predictors['mean'] = [np.mean(allmeans_gdppcs), np.mean(allmeans_density)] # don't use mean density-- all should have
        for region in econ_predictors:
            if econ_predictors[region][0] is None:
                econ_predictors[region][0] = rm_init([econ_predictors['mean'][0]])
            if econ_predictors[region][1] is None:
                econ_predictors[region][1] = rm_init([econ_predictors['mean'][1]])

        self.econ_predictors = econ_predictors

        self.economicmodel = economicmodel

    def get_econ_predictors(self, region):
        gdppcsdensity = self.econ_predictors.get(region, None)

        if gdppcsdensity is None:
            gdppcs = self.econ_predictors['mean'][0]
        else:
            gdppcs = rm_mean(gdppcsdensity[0])

        if gdppcsdensity is None:
            density = self.econ_predictors['mean'][1]
        else:
            density = rm_mean(gdppcsdensity[1])

        return [gdppcs, density]

    def get_baseline(self, region):
        #assert region in self.temp_predictors, "Missing " + region
        return (map(rm_mean, self.temp_predictors[region]) + map(np.log, self.get_econ_predictors(region)),)

    def get_update(self, region, year, temps):
        """Allow temps = None for dumb farmer who cannot adapt to temperature."""
        if temps is not None:
            di = 0
            belowprev = 0
            for ii in range(len(self.binlimits) - 2):
                belowupper = float(np.sum(temps < self.binlimits[ii+1]))

                if ii == self.dropbin:
                    belowprev = belowupper
                    di = -1
                    continue

                rm_add(self.temp_predictors[region][ii+di], belowupper - belowprev, self.numtempyears)
                belowprev = belowupper
            rm_add(self.temp_predictors[region][-1], len(temps) - belowprev, self.numtempyears)

        if region in self.econ_predictors:
            gdppc = self.economicmodel.get_gdppc_year(region, year)
            if gdppc is not None:
                rm_add(self.econ_predictors[region][0], gdppc, self.numeconyears)

            popop = self.economicmodel.get_popop_year(region, year)
            if popop is not None:
                rm_add(self.econ_predictors[region][1], popop, self.numeconyears)

            logecons = [np.log(rm_mean(self.econ_predictors[region][0])),
                        np.log(rm_mean(self.econ_predictors[region][1]))]
            return (map(rm_mean, self.temp_predictors[region]) + logecons,)
        else:
            return (map(rm_mean, self.temp_predictors[region]) + map(np.log, self.get_econ_predictors(region)),)

region_stepcurves = {}

class InstantAdaptingStepCurve(AdaptableCurve):
    def __init__(self, beta_generator, get_predictors):
        self.beta_generator = beta_generator
        self.get_predictors = get_predictors
        self.region = None
        self.curr_curve = None

    def create(self, region, predictors):
        copy = self.__class__(self.beta_generator, self.get_predictors)
        copy.region = region
        copy.curr_curve = self.beta_generator.get_curve(predictors, None)
        region_stepcurves[region] = copy
        copy.min_beta = np.minimum(0, np.nanmin(np.array(copy.curr_curve.yy)[4:-2]))
        return copy

    def update(self, year, temps):
        predictors = self.get_predictors(self.region, year, temps)
        self.curr_curve = self.beta_generator.get_curve(predictors, self.min_beta)

    def __call__(self, x):
        return self.curr_curve(x)

class ComatoseInstantAdaptingStepCurve(InstantAdaptingStepCurve):
    def __init__(self, beta_generator, get_predictors):
        super(ComatoseInstantAdaptingStepCurve, self).__init__(beta_generator, get_predictors)

    def update(self, year, temps):
        # Ignore for the comatose farmer
        pass

class DumbInstantAdaptingStepCurve(InstantAdaptingStepCurve):
    def __init__(self, beta_generator, get_predictors):
        super(DumbInstantAdaptingStepCurve, self).__init__(beta_generator, get_predictors)

    def update(self, year, temps):
        # Set temps to None so no adaptation to them
        super(DumbInstantAdaptingStepCurve, self).update(year, None)

class AdaptingStepCurve(AdaptableCurve):
    def __init__(self, beta_generator, gamma_generator, get_predictors):
        self.beta_generator = beta_generator
        self.gamma_generator = gamma_generator
        self.get_predictors = get_predictors
        self.region = None
        self.curr_curve = None

    def create(self, region, predictors):
        copy = AdaptingStepCurve(self.beta_generator, self.gamma_generator, self.get_predictors)
        copy.region = region
        copy.curr_curve = self.beta_generator.get_curve(predictors)
        return copy

    def update(self, year, temps):
        predictors = self.get_predictors(region, year, temps)
        final_curve = self.beta_generator.get_curve(predictors)
        gamma_curve = self.gamma_generator.get_curve(predictors)

        yy = []
        for x in self.curr_curve.get_xx():
            gamma = gamma_curve(x)
            if gamma >= 0:
                yy.append(self.curr_curve(x))
            else:
                expgamma = np.exp(gamma)
                newbeta = self.curr_curve(x) * expgamma + final_curve(x) * (1 - expgamma)
                yy.append(newbeta)

        self.curr_curve = StepCurve(self.curr_curve.xxlimits, yy)

    def __call__(self, x):
        return self.curr_curve(x)
