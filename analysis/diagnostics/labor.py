"""
This script apparently serves as a sanity check.

This script checks projection output is checked against values calculated here.

The script is intended to be run as::

    python <path_to_script> <path_to_directory_of_projection_output>


Key variables, set at the head of this scripts main() file will need to be
set and possibly updated.
"""

import os

import numpy as np

import lib


def cal_proj(tasmax, gammas, belowzero):
    """Quickly calc impact projection

    Applies a polynomial to some climate variables.
    """
    # if tas > 0: dot product, otherwise: belowzero;
    out = np.where(tasmax[0] > 0, np.dot(gammas, tasmax), belowzero)
    return out


def main(projout_dir):
    """Run proj calcs from scratch, print comparison with output

    Parameters
    ----------
    projout_dir : str
        Full path to projection diagnostic output directory.
    """
    climate_variables = ['tasmax', 'tasmax-poly-2', 'tasmax-poly-3', 'tasmax-poly-4']
    weathertemplate = "/shares/gcp/climate/BCSD/hierid/popwt/daily/{variable}/{rcp}/CCSM4/{year}/1.0.nc4"
    csvvmodel = "labor_test"
    model_lowrisk = "labor_test-risklow"
    futureyear = 2050
    region = 'USA.14.608'  # 'IND.33.542.2153'
    polyorder = 4

    lib.show_header("The Predictors File (allcalcs):")
    calcs_lowrisk = lib.get_excerpt(os.path.join(projout_dir, "labor-allcalcs-%s.csv" % model_lowrisk),
                                    2, region,
                                    range(2000, 2011) + [futureyear - 1, futureyear],
                                    hasmodel=False)

    lib.show_header("Weather:")
    weathers = {}
    for v in climate_variables:
        lib.show_header(' %s:' % v)
        weathers[v] = lib.get_weather(weathertemplate,
                                      [1981] + list(range(2001, 2011)) + [futureyear - 1, futureyear],
                                      region, variable=v)

    lib.show_header("CSVV:")
    csvv = lib.get_csvv("/shares/gcp/social/parameters/labor/csvv_oct2019/%s.csvv" % csvvmodel)

    lib.show_header("Outputs:")
    outputs = lib.get_outputs(os.path.join(projout_dir, model_lowrisk + '.nc4'), [1981, futureyear - 1, futureyear],
                              region)

    # Some variables we need to calc the projections below.
    gammas_lowrisk = np.stack([csvv['gamma'][i] for i in range(polyorder)])
    belowzero_lowrisk = csvv['gamma'][polyorder]

    lib.show_header("Un-rebased value in 1981 (%.12g reported)" % outputs[1981]['sum'])
    # Calc 1981 by hand...
    ybar = np.mean(
        cal_proj(tasmax=np.stack([weathers[p][1981] for p in climate_variables]),
                 gammas=gammas_lowrisk,
                 belowzero=belowzero_lowrisk)
    )
    print('\t Calculated: %.12g' % ybar)

    # Calc baseline by hand
    lib.show_header("Baseline (%.12g reported):" % lib.excind(calcs_lowrisk, 2000, 'baseline'))

    # Project for baseline range and then take population mean.
    basevals = []
    for x in range(2001, 2011):
        basevals.append(
            cal_proj(tasmax=np.stack([weathers[p][x] for p in climate_variables]),
                     gammas=gammas_lowrisk,
                     belowzero=belowzero_lowrisk)
        )
    basevals_bar = np.mean(np.array(basevals))
    print('\t Calculated: %.12g' % basevals_bar)

    # Calc rebased future value
    lib.show_header("Rebased future result (%.12g reported)" % (outputs[futureyear]['rebased']))
    ybar_future = cal_proj(tasmax=np.stack([weathers[p][futureyear] for p in climate_variables]),
                           gammas=gammas_lowrisk,
                           belowzero=belowzero_lowrisk)
    yrebase = np.mean(ybar_future) - basevals_bar
    print('\t Calculated: %.12g' % yrebase)


if __name__ == '__main__':
    import sys

    main(projout_dir=sys.argv[1])
