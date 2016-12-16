import copy, os
import numpy as np
from openest.models.curve import StepCurve, AdaptableCurve
from econmodel import *

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

class Predictorator(object):
    def __init__(self, economicmodel, numeconyears, maxbaseline):
        self.numeconyears = numeconyears

        self.econ_predictors = economicmodel.baseline_prepared(maxbaseline, numeconyears, rm_init)
        self.economicmodel = economicmodel

        self.startupdateyear = maxbaseline

    def get_econ_predictors(self, region):
        econpreds = self.econ_predictors.get(region, None)

        if econpreds is None:
            gdppcs = self.econ_predictors['mean']['gdppcs']
        else:
            gdppcs = rm_mean(gdppcsdensity['gdppcs'])

        if econpreds is None:
            density = self.econ_predictors['mean']['popop']
        else:
            density = rm_mean(gdppcsdensity['popop'])

        return dict(gdppc=gdppcs, popop=density)

    def get_baseline(self, region):
        raise NotImplementedError

    def get_update(self, region, year, weather):
        raise NotImplementedError

class TemperatureIncomeDensityPredictorator(Predictorator):
    def __init__(self, weatherbundle, economicmodel, numtempyears, numeconyears, maxbaseline):
        super(TemperatureIncomeDensityPredictorator, self).__init__(economicmodel, numeconyears, maxbaseline)

        self.numtempyears = numtempyears

        print "Collecting baseline information..."
        temp_predictors = {}
        for region, temps in weatherbundle.baseline_values(maxbaseline): # baseline through maxbaseline
            temp_predictors[region] = rm_init(temps[-numtempyears:])

        self.temp_predictors = temp_predictors

    def get_baseline(self, region):
        #assert region in self.temp_predictors, "Missing " + region
        econpreds = self.get_econ_predictors(region)
        return {self.weatherbundle.get_dimension()[0]: rm_mean(self.temp_predictors[region]),
                'loggdppc': np.log(econpreds['gdppc']), 'logpopop': np.log(econpreds['popop'])}

    def get_update(self, region, year, temps):
        """Allow temps = None for dumb farmer who cannot adapt to temperature."""
        assert year < 10000

        if temps is not None and year > self.startupdateyear:
            rm_add(self.temp_predictors[region], np.mean(temps), self.numtempyears)

        if region in self.econ_predictors:
            gdppc = self.economicmodel.get_gdppc_year(region, year)
            if gdppc is not None and year > self.startupdateyear:
                rm_add(self.econ_predictors[region]['gdppcs'], gdppc, self.numeconyears)

            popop = self.economicmodel.get_popop_year(region, year)
            if popop is not None and year > self.startupdateyear:
                rm_add(self.econ_predictors[region]['popop'], popop, self.numeconyears)

            return {self.weatherbundle.get_dimension()[0]: rm_mean(self.temp_predictors[region]),
                    'loggdppc': np.log(rm_mean(self.econ_predictors[region]['gdppcs'])),
                    'logpopop': np.log(rm_mean(self.econ_predictors[region]['popop']))}
        else:
            return {self.weatherbundle.get_dimension()[0]: rm_mean(self.temp_predictors[region]),
                    'loggdppc': np.log(self.get_econ_predictors(region)['gdppc']),
                    'logpopop': np.log(self.get_econ_predictors(region)['popop'])}

class BinsIncomeDensityPredictorator(Predictorator):
    def __init__(self, weatherbundle, economicmodel, binlimits, dropbin, numtempyears, numeconyears, maxbaseline):
        super(TemperatureIncomeDensityPredictorator, self).__init__(economicmodel, numeconyears, maxbaseline)

        self.binlimits = binlimits
        self.dropbin = dropbin
        self.numtempyears = numtempyears

        print "Collecting baseline information..."
        temp_predictors = {} # {region: [rm-bin-1, ...]}
        for region, binyears in weatherbundle.baseline_values(maxbaseline): # baseline through maxbaseline
            usedbinyears = []
            for kk in range(binyears.shape[-1]):
                if kk == dropbin:
                    continue
                usedbinyears.append(rm_init(binyears[-numtempyears:, kk]))
            temp_predictors[region] = usedbinyears

        self.temp_predictors = temp_predictors

    def get_baseline(self, region):
        #assert region in self.temp_predictors, "Missing " + region
        assert len(self.weatherbundle.get_dimension()) == len(self.temp_predictors[region])
        preds = {self.weatherbundle.get_dimension()[ii]: rm_mean(self.temp_predictors[region][ii]) for ii in range(len(self.weatherbundle.get_dimension()))}

        econpreds = self.get_econ_predictors(region)
        preds['loggdppc'] = np.log(econpreds['gdppc'])
        preds['logpopop'] = np.log(econpreds['popop'])

    def get_update(self, region, year, temps):
        assert year < 10000

        """Allow temps = None for dumb farmer who cannot adapt to temperature."""
        if temps is not None and year > self.startupdateyear:
            if len(temps.shape) == 2:
                if temps.shape[0] == 12 and temps.shape[1] == len(self.binlimits) - 1:
                    di = 0
                    for kk in range(len(self.binlimits) - 1):
                        if kk == self.dropbin:
                            di = -1
                            continue

                        rm_add(self.temp_predictors[region][kk+di], np.sum(temps[:, kk]), self.numtempyears)
                else:
                    raise RuntimeError("Unknown format for temps")
            else:
                di = 0
                belowprev = 0
                for kk in range(len(self.binlimits) - 2):
                    belowupper = float(np.sum(temps < self.binlimits[kk+1]))

                    if kk == self.dropbin:
                        belowprev = belowupper
                        di = -1
                        continue

                    rm_add(self.temp_predictors[region][kk+di], belowupper - belowprev, self.numtempyears)
                    belowprev = belowupper
                rm_add(self.temp_predictors[region][-1], len(temps) - belowprev, self.numtempyears)

        if region in self.econ_predictors:
            gdppc = self.economicmodel.get_gdppc_year(region, year)
            if gdppc is not None and year > self.startupdateyear:
                rm_add(self.econ_predictors[region]['gdppcs'], gdppc, self.numeconyears)

            popop = self.economicmodel.get_popop_year(region, year)
            if popop is not None and year > self.startupdateyear:
                rm_add(self.econ_predictors[region]['popop'], popop, self.numeconyears)
        else:
            gdppc = self.get_econ_predictors(region)['gdppc']
            popop = self.get_econ_predictors(region)['popop']

        preds = {self.weatherbundle.get_dimension()[ii]: rm_mean(self.temp_predictors[region][ii]) for ii in range(len(self.weatherbundle.get_dimension()))}
        preds['loggdppc'] = np.log(gdppc)
        preds['logpopop'] = np.log(popop)

        return preds
        
region_stepcurves = {}

class InstantAdaptingStepCurve(AdaptableCurve):
    def __init__(self, beta_generator, get_predictors, bin_limits):
        self.beta_generator = beta_generator
        self.get_predictors = get_predictors
        self.region = None
        self.curr_curve = None
        self.bin_limits = bin_limits

        bin_limits = np.array(bin_limits)
        if bin_limits[0] == -np.inf:
            bin_limits[0] = bin_limits[1] - 10
        if bin_limits[-1] == np.inf:
            bin_limits[-1] = bin_limits[-2] + 10
        self.xx = (bin_limits[1:] + bin_limits[:-1]) / 2

    def create(self, region, predictors):
        copy = self.__class__(self.beta_generator, self.get_predictors, self.bin_limits)
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
    def __init__(self, beta_generator, get_predictors, bin_limits):
        super(ComatoseInstantAdaptingStepCurve, self).__init__(beta_generator, get_predictors, bin_limits)

    def update(self, year, temps):
        # Ignore for the comatose farmer
        pass

class DumbInstantAdaptingStepCurve(InstantAdaptingStepCurve):
    def __init__(self, beta_generator, get_predictors, bin_limits):
        super(DumbInstantAdaptingStepCurve, self).__init__(beta_generator, get_predictors, bin_limits)

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
