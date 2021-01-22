"""Functions to support constraints applied to a projection.

Currently the only constraint defined here is "Good money", since
beta-clipping requires no complicate functions and U-clipping has been
moved to open-estimate.
"""

import csv
import os
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
    baseline_loggdppc = {r: covariator.get_current(r)['loggdppc'] for r in weatherbundle.regions}

    # Get marginals on loggdppc (assumed to be constant)
    loggdppc_marginals = curvegen.get_marginals('loggdppc')
    loggdppc_marginals = np.array(
        [loggdppc_marginals[predname] for predname in curvegen.prednames]  # same order as temps
    )

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
    return get_curve_extrema(regions, curvegen, covariator, mint, maxt, analytic, 'boatpose', 'minpath')


def get_curve_maxima(regions, curvegen, covariator, mint, maxt, analytic):
    # Determine maximum value of curve between mint and maxt
    print("Determining maximum temperatures.")
    return get_curve_extrema(regions, curvegen, covariator, mint, maxt, analytic, 'downdog', 'maxpath')


def get_curve_extrema(regions, curvegen, covariator, mint, maxt, analytic, direction, extpathkey):
    baselinecurves = {}
    baselineexts = {}

    if caller.callinfo and extpathkey in caller.callinfo:

        if direction not in ['boatpose', 'downdog']:
            raise ValueError("'direction' must be 'boatpose' or 'downdog'")

        with open(caller.callinfo[extpathkey], 'w') as fp:
            writer = csv.writer(fp)
            writer.writerow(['region', 'brute', 'analytic'])
            for region in regions:
                try:
                    curve = curvegen.get_curve(region, 2005, covariator.get_current(region))
                except KeyError:  # If current region isn't available...
                    continue
                baselinecurves[region] = curve
                if isinstance(mint, dict):
                    temps = np.arange(np.floor(mint[region]), np.ceil(maxt[region])+1)
                else:
                    temps = np.arange(mint, maxt+1)
                if direction == 'boatpose':
                    exttemp = temps[np.argmin(curve.univariate(temps))]
                else:
                    exttemp = temps[np.argmax(curve.univariate(temps))]
                exttemp2 = analytic(curve)
                if np.abs(exttemp - exttemp2) > 1:
                    print("WARNING: %s has unclear exttemp: %f, %f" % (region, exttemp, exttemp2))
                baselineexts[region] = exttemp2
                writer.writerow([region, exttemp, exttemp2])
        os.chmod(caller.callinfo[extpathkey], 0o664)
    else:
        for region in regions:
            try:
                curve = curvegen.get_curve(region, 2005, covariator.get_current(region))
            except KeyError:  # If region isn't available (e.g. for diagnostic runs)...
                continue
            baselinecurves[region] = curve
            exttemp2 = analytic(curve)
            baselineexts[region] = exttemp2

    return baselinecurves, baselineexts
