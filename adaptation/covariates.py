import numpy as np
from econmodel import *
from datastore import agecohorts

## Management of rolling means
## Rolling mean is [SUM, COUNT]

def rm_init(values):
    return [sum(values), len(values)]

def rm_add(rm, value, maxvalues):
    assert rm[1] <= maxvalues, "{0} > {1}".format(rm[1], maxvalues)

    if rm[1] >= maxvalues:
        rm[0] = (maxvalues - 1) * rm[0] / rm[1] + value
        if rm[1] > maxvalues:
            rm[1] = maxvalues
    else:
        rm[0] += value
        rm[1] += 1

def rm_mean(rm):
    return rm[0] / rm[1]

class Covariator(object):
    def __init__(self, maxbaseline):
        self.startupdateyear = maxbaseline

    def get_baseline(self, region):
        raise NotImplementedError

    def get_update(self, region, year, weather):
        raise NotImplementedError

class EconomicCovariator(Covariator):
    def __init__(self, economicmodel, numeconyears, maxbaseline):
        super(EconomicCovariator, self).__init__(maxbaseline)
        
        self.numeconyears = numeconyears

        self.econ_predictors = economicmodel.baseline_prepared(maxbaseline, numeconyears, rm_init)
        self.economicmodel = economicmodel

    def get_econ_predictors(self, region):
        econpreds = self.econ_predictors.get(region, None)

        if econpreds is None:
            gdppcs = self.econ_predictors['mean']['gdppcs']
        else:
            gdppcs = rm_mean(econpreds['gdppcs'])

        if econpreds is None:
            density = self.econ_predictors['mean']['popop']
        else:
            density = rm_mean(econpreds['popop'])

        return dict(gdppc=gdppcs, popop=density)

    def get_baseline(self, region):
        econpreds = self.get_econ_predictors(region)
        return dict(loggdppc=np.log(econpreds['gdppc']),
                    logpopop=np.log(econpreds['popop']))

    def get_update(self, region, year, temps):
        assert year < 10000

        if region in self.econ_predictors:
            gdppc = self.economicmodel.get_gdppc_year(region, year)
            if gdppc is not None and year > self.startupdateyear:
                rm_add(self.econ_predictors[region]['gdppcs'], gdppc, self.numeconyears)

            popop = self.economicmodel.get_popop_year(region, year)
            if popop is not None and year > self.startupdateyear:
                rm_add(self.econ_predictors[region]['popop'], popop, self.numeconyears)

        gdppc = self.get_econ_predictors(region)['gdppc']
        popop = self.get_econ_predictors(region)['popop']

        return dict(loggdppc=np.log(gdppc), logpopop=np.log(popop))

class MeanWeatherCovariator(Covariator):
    def __init__(self, weatherbundle, numtempyears, maxbaseline):
        super(MeanWeatherCovariator, self).__init__(maxbaseline)

        self.numtempyears = numtempyears

        print "Collecting baseline information..."
        temp_predictors = {}
        for region, temps in weatherbundle.baseline_values(maxbaseline): # baseline through maxbaseline
            temp_predictors[region] = rm_init(temps[-numtempyears:])

        self.temp_predictors = temp_predictors
        self.weatherbundle = weatherbundle

    def get_baseline(self, region):
        #assert region in self.temp_predictors, "Missing " + region
        return {self.weatherbundle.get_dimension()[0]: rm_mean(self.temp_predictors[region])}

    def get_update(self, region, year, temps):
        """Allow temps = None for dumb farmer who cannot adapt to temperature."""
        assert year < 10000

        if temps is not None and year > self.startupdateyear:
            rm_add(self.temp_predictors[region], np.mean(temps), self.numtempyears)

        return {self.weatherbundle.get_dimension()[0]: rm_mean(self.temp_predictors[region])}

class MeanBinsCovariator(Covariator):
    def __init__(self, weatherbundle, binlimits, dropbin, numtempyears, maxbaseline):
        super(MeanBinsCovariator, self).__init__(maxbaseline)

        self.binlimits = binlimits
        self.dropbin = dropbin
        self.numtempyears = numtempyears

        print "Collecting baseline information..."
        temp_predictors = {} # {region: [rm-bin-1, ...]}
        for region, binyears in weatherbundle.baseline_values(maxbaseline): # baseline through maxbaseline
            usedbinyears = []
            for kk in range(binyears.shape[-1]):
                usedbinyears.append(rm_init(binyears[-numtempyears:, kk]))
            temp_predictors[region] = usedbinyears

        self.temp_predictors = temp_predictors
        self.weatherbundle = weatherbundle

    def get_baseline(self, region):
        #assert region in self.temp_predictors, "Missing " + region
        assert len(self.weatherbundle.get_dimension()) == len(self.temp_predictors[region])
        return {self.weatherbundle.get_dimension()[ii]: rm_mean(self.temp_predictors[region][ii]) for ii in range(len(self.weatherbundle.get_dimension()))}

    def get_update(self, region, year, temps):
        assert year < 10000

        """Allow temps = None for dumb farmer who cannot adapt to temperature."""
        if temps is not None and year > self.startupdateyear:
            if len(temps.shape) == 2:
                if temps.shape[0] == 12 and temps.shape[1] == len(self.binlimits) - 1:
                    for kk in range(len(self.binlimits) - 1):
                        rm_add(self.temp_predictors[region][kk], np.sum(temps[:, kk]), self.numtempyears)
                else:
                    raise RuntimeError("Unknown format for temps")
            else:
                belowprev = 0
                for kk in range(len(self.binlimits) - 2):
                    belowupper = float(np.sum(temps < self.binlimits[kk+1]))

                    rm_add(self.temp_predictors[region][kk], belowupper - belowprev, self.numtempyears)
                    belowprev = belowupper
                rm_add(self.temp_predictors[region][-1], len(temps) - belowprev, self.numtempyears)

        return {self.weatherbundle.get_dimension()[ii]: rm_mean(self.temp_predictors[region][ii]) for ii in range(len(self.weatherbundle.get_dimension()))}

class AgeShareCovariator(Covariator):
    def __init__(self, economicmodel, numeconyears, maxbaseline):
        super(AgeShareCovariator, self).__init__(maxbaseline)
        
        self.numeconyears = numeconyears

        self.ageshares = agecohorts.load_ageshares(economicmodel.model, economicmodel.scenario)
        self.economicmodel = economicmodel

        self.agerm = {}
        self.get_baseline('mean') # Fill in the mean agerm

    def get_baseline(self, region):
        # Fill in the rm for this region
        if region != 'mean':
            region = region[:3] # Just country code
        if region not in self.ageshares:
            return {column: rm_mean(self.agerm['mean'][column]) for column in agecohorts.columns}
        
        rmdata = {column: [] for column in agecohorts.columns} # {agecolumn: [values]}
        
        for year in range(min(self.ageshares[region].keys()), self.startupdateyear+1):
            if year in self.ageshares[region]:
                for cc in range(len(agecohorts.columns)):
                    rmdata[agecohorts.columns[cc]].append(self.ageshares[region][year][cc])

        for column in rmdata:
            rmdata[column] = rm_init(rmdata[column][-self.numeconyears:])

        self.agerm[region] = rmdata
        
        return {column: rm_mean(rmdata[column]) for column in agecohorts.columns}

    def get_update(self, region, year, temps):
        region = region[:3] # Just country code
        if region not in self.ageshares:
            region = 'mean' # XXX: This updates for every country!

        if region in self.agerm:
            if year in self.ageshares[region]:
                for cc in range(len(agecohorts.columns)):
                    rm_add(self.agerm[region][agecohorts.columns[cc]], self.ageshares[region][year][cc], self.numeconyears)

        return {column: rm_mean(self.agerm[region][column]) for column in agecohorts.columns}

class CombinedCovariator(Covariator):
    def __init__(self, covariators):
        for covariator in covariators[1:]:
            assert covariator.startupdateyear == covariators[0].startupdateyear
        
        super(CombinedCovariator, self).__init__(covariators[0].startupdateyear)
        self.covariators = covariators

    def get_baseline(self, region):
        result = {}
        for covariator in self.covariators:
            subres = covariator.get_baseline(region)
            for key in subres:
                result[key] = subres[key]

        return result

    def get_update(self, region, year, temps):
        result = {}
        for covariator in self.covariators:
            subres = covariator.get_update(region, year, temps)
            for key in subres:
                result[key] = subres[key]

        return result