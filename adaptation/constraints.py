import numpy as np

def make_get_coeff_goodmoney(weatherbundle, covariator, curvegen, baselinemins, curve_get_coeff, flipsign=False):
    # Generating all curves, for baseline
    baseline_loggdppc = {}
    for region in weatherbundle.regions:
        baseline_loggdppc[region] = covariator.get_baseline(region)['loggdppc']

    loggdppc_marginals = curvegen.get_marginals('loggdppc')
    loggdppc_marginals = np.array([loggdppc_marginals[predname] for predname in curvegen.prednames]) # same order as temps

    signcoeff = -1 if flipsign else 1

    def coeff_getter(region, year, temps, curve):        
        mareff = np.sum(loggdppc_marginals * (temps - baselinemins[region]))
        if mareff > 0:
            deltaloggdppc = covariator.get_baseline(region)['loggdppc'] - baseline_loggdppc[region] # get_baseline gives current sense, not really baseline
            return curve_get_coeff(curve) - signcoeff * deltaloggdppc * loggdppc_marginals
        else:
            return curve_get_coeff(curve)
    return coeff_getter
