"""Functions to support constraints applied to a projection.

Currently the only constraint defined here is "Good money", since
beta-clipping requires no complicate functions and U-clipping has been
moved to open-estimate.
"""

import csv, os
import numpy as np
from generate import caller

"""
The "Good Money" condition:
An increase in your wealth will always decrease your sensitivity.

Let your response be defined by f(x | gdppc), for weather x, conditional on gdppc.
We want to ensure that
(df / dgdppc)(x) has a sign in the direction of less sensitivity.

For each x, f(x | gdppc_t) against f(x | gdppc_0) and take the better of the two.
"""

def make_get_coeff_goodmoney(weatherbundle, covariator, curvegen, baselinemins, curve_get_coeff, flipsign=False):
    # Record all baseline log GDP p.c.
    baseline_loggdppc = {}
    for region in weatherbundle.regions:
        baseline_loggdppc[region] = covariator.get_current(region)['loggdppc']

    # Get marginals on loggdppc (assumed to be constant)
    loggdppc_marginals = curvegen.get_marginals('loggdppc')
    loggdppc_marginals = np.array([loggdppc_marginals[predname] for predname in curvegen.prednames]) # same order as temps

    # flipsign = True when subtracting off baseline
    signcoeff = -1 if flipsign else 1

    def coeff_getter(region, year, temps, curve):
        # Is the marginal effect positive (that is, toward more bad stuff)?
        mareff = np.sum(loggdppc_marginals * (temps - baselinemins[region]))
        if mareff > 0:
            deltaloggdppc = covariator.get_current(region)['loggdppc'] - baseline_loggdppc[region]
            return curve_get_coeff(curve) - signcoeff * deltaloggdppc * loggdppc_marginals
        else:
            return curve_get_coeff(curve)
    return coeff_getter

def get_curve_minima(regions, curvegen, covariator, mint, maxt, analytic):
    # Determine minimum value of curve between mint and maxt
    print("Determining minimum temperatures.")
    baselinecurves = {}
    baselinemins = {}

    if caller.callinfo and 'minpath' in caller.callinfo:
        with open(caller.callinfo['minpath'], 'w') as fp:
            writer = csv.writer(fp)
            writer.writerow(['region', 'brute', 'analytic'])
            for region in regions:
                curve = curvegen.get_curve(region, 2005, covariator.get_current(region))
                baselinecurves[region] = curve
                if isinstance(mint, dict):
                    temps = np.arange(np.floor(mint[region]), np.ceil(maxt[region])+1)
                else:
                    temps = np.arange(mint, maxt+1)
                mintemp = temps[np.argmin(curve(temps))]
                mintemp2 = analytic(region, curve)
                if np.abs(mintemp - mintemp2) > 1:
                    print(("WARNING: %s has unclear mintemp: %f, %f" % (region, mintemp, mintemp2)))
                baselinemins[region] = mintemp2
                writer.writerow([region, mintemp, mintemp2])
        os.chmod(caller.callinfo['minpath'], 0o664)
    else:
        for region in regions:
            curve = curvegen.get_curve(region, 2005, covariator.get_current(region))
            baselinecurves[region] = curve
            mintemp2 = analytic(region, curve)
            baselinemins[region] = mintemp2

    return baselinecurves, baselinemins
