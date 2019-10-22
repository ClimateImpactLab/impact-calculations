"""
This script apparently serves as a sanity check.

This script checks projection output is checked against values calculated here.

The script is intended to be run as::

    python <path_to_script> <path_to_directory_of_projection_output>


Key global variables, set at the head of this script file will need to be
set and possibly updates. This script also assumes that a Julia shell is
available from the run environment.
"""

import os
import numpy as np
import lib


def cal_proj(year, weathers, climate_variables, polyorder, csvv):
    """Quickly calc impact projection"""
    year = int(year)
    tas = np.stack([weathers[p][year] for p in climate_variables])
    gammas = np.stack([csvv['gamma'][i] for i in range(polyorder)])
    belowzero = csvv['gamma'][polyorder]
    # if tas > 0: dot product, otherwise: belowzero; then take population
    # mean.
    out = np.where(tas[0] > 0, np.dot(gammas, tas), belowzero)
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
    model = "labor_test-risklow"
    futureyear = 2050
    region = 'USA.14.608'  # 'IND.33.542.2153'
    polyorder = 4

    lib.show_header("The Predictors File (allcalcs):")
    calcs = lib.get_excerpt(os.path.join(projout_dir, "labor-allcalcs-%s.csv" % model),
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
    outputs = lib.get_outputs(os.path.join(projout_dir, model + '.nc4'), [1981, futureyear - 1, futureyear], region)

    lib.show_header("Un-rebased value in 1981 (%.12g reported)" % outputs[1981]['sum'])

    # Calc 1981 by hand...
    ybar = np.mean(cal_proj(1981, weathers, climate_variables, polyorder, csvv))
    lib.show_header("Un-rebased value in 1981 (%.12g calculated)" % ybar)

    # Calc baseline by hand
    lib.show_header("Baseline (%.12g reported):" % lib.excind(calcs, 2000, 'baseline'))
    basevals = np.array([cal_proj(x, weathers, climate_variables, polyorder, csvv) for x in range(2001, 2011)])
    basevals_bar = np.mean(basevals)
    lib.show_header("Baseline (%.12g calculated):" % basevals_bar)

    # Calc rebased future value
    lib.show_header("Rebased future result (%.12g reported)" % (outputs[futureyear]['rebased']))
    ybar_future = cal_proj(futureyear, weathers, climate_variables, polyorder,
                           csvv)
    yrebase = np.mean(ybar_future) - basevals_bar
    lib.show_header("Rebased future result (%.12g calculated)" % yrebase)


if __name__ == '__main__':
    import sys

    main(projout_dir=sys.argv[1])
