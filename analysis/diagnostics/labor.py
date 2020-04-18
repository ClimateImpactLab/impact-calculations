"""
This script checks projection output against calculated values.

This is intended to be run as::

    python <path_to_script> <path_to_directory_of_projection_output>


Key global variables, set at the head of this script will need to be
set and updated.
"""

import os

import numpy as np

import lib


CLIMATE_VARIABLES = ['tasmax', 'tasmax-poly-2', 'tasmax-poly-3', 'tasmax-poly-4']
WEATHERTEMPLATE = "/shares/gcp/climate/BCSD/hierid/popwt/daily/{variable}/{rcp}/CCSM4/{year}/1.0.nc4"
CSVVMODEL = "labor_test"
MODEL_LOWRISK = "labor_test-risklow"
MODEL_HIGHRISK = "labor_test-riskhigh"
FUTUREYEAR = 2050
REGION = 'USA.14.608'  # 'IND.33.542.2153'
POLYORDER = 4


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
    lib.show_header("The Predictors File lowrisk (allcalcs):")
    calcs_lowrisk = lib.get_excerpt(os.path.join(projout_dir, "labor-allcalcs-%s.csv" % MODEL_LOWRISK),
                                    2, REGION,
                                    range(2000, 2011) + [FUTUREYEAR - 1, FUTUREYEAR],
                                    hasmodel=False)

    lib.show_header("The Predictors File highrisk (allcalcs):")
    calcs_highrisk = lib.get_excerpt(os.path.join(projout_dir, "labor-allcalcs-%s.csv" % MODEL_HIGHRISK),
                                     2, REGION,
                                     range(2000, 2011) + [FUTUREYEAR - 1, FUTUREYEAR],
                                     hasmodel=False)

    lib.show_header("Weather:")
    weathers = {}
    for v in CLIMATE_VARIABLES:
        lib.show_header(' %s:' % v)
        weathers[v] = lib.get_weather(WEATHERTEMPLATE,
                                      [1981] + list(range(2001, 2011)) + [FUTUREYEAR - 1, FUTUREYEAR],
                                      REGION, variable=v)

    lib.show_header("CSVV:")
    csvv = lib.get_csvv("/shares/gcp/social/parameters/labor/csvv_oct2019/%s.csvv" % CSVVMODEL)

    lib.show_header("Outputs, lowrisk:")
    outputs_lowrisk = lib.get_outputs(os.path.join(projout_dir, MODEL_LOWRISK + '.nc4'),
                                      [1981, FUTUREYEAR - 1, FUTUREYEAR],
                                      REGION)

    lib.show_header("Outputs, highrisk:")
    outputs_highrisk = lib.get_outputs(os.path.join(projout_dir, MODEL_HIGHRISK + '.nc4'),
                                       [1981, FUTUREYEAR - 1, FUTUREYEAR],
                                       REGION)

    # Some variables we need to calc the projections below.
    gammas_lowrisk = np.stack([csvv['gamma'][i] for i in range(POLYORDER)])
    belowzero_lowrisk = csvv['gamma'][POLYORDER]
    grp_offset = POLYORDER + 1  # Because gammas are stacked on one-another.
    belowzero_highrisk = csvv['gamma'][POLYORDER + grp_offset]
    gammas_highrisk = np.stack([csvv['gamma'][i + grp_offset] for i in range(POLYORDER)])

    # Output depending on calculated projections.
    lib.show_header("Un-rebased, lowrisk value in 1981 (%.12g reported)" % outputs_lowrisk[1981]['sum'])
    tasmaxs = np.stack([weathers[p][1981] for p in CLIMATE_VARIABLES])
    ybar = np.mean(cal_proj(tasmax=tasmaxs,
                            gammas=gammas_lowrisk,
                            belowzero=belowzero_lowrisk))
    print('\t Calculated: %.12g' % ybar)
    lib.show_header("Un-rebased, highrisk value in 1981 (%.12g reported)" % outputs_highrisk[1981]['sum'])
    ybar = np.mean(cal_proj(tasmax=tasmaxs,
                            gammas=gammas_highrisk,
                            belowzero=belowzero_highrisk))
    print('\t Calculated: %.12g' % ybar)

    # Calc baseline by hand
    lib.show_header("Baseline, lowrisk (%.12g reported):" % lib.excind(calcs_lowrisk, 2000, 'baseline'))
    # Project for baseline range and then take population mean.
    basevals = []
    for x in range(2001, 2011):
        basevals.append(
            cal_proj(tasmax=np.stack([weathers[p][x] for p in CLIMATE_VARIABLES]),
                     gammas=gammas_lowrisk,
                     belowzero=belowzero_lowrisk)
        )
    basevals_bar_lowrisk = np.mean(np.array(basevals))
    print('\t Calculated: %.12g' % basevals_bar_lowrisk)
    lib.show_header("Baseline, highrisk (%.12g reported):" % lib.excind(calcs_highrisk, 2000, 'baseline'))
    # Project for baseline range and then take population mean.
    basevals = []
    for x in range(2001, 2011):
        basevals.append(
            cal_proj(tasmax=np.stack([weathers[p][x] for p in CLIMATE_VARIABLES]),
                     gammas=gammas_highrisk,
                     belowzero=belowzero_highrisk)
        )
    basevals_bar_highrisk = np.mean(np.array(basevals))
    print('\t Calculated: %.12g' % basevals_bar_highrisk)

    # Calc rebased future value
    lib.show_header("Rebased, lowrisk future result (%.12g reported)" % (outputs_lowrisk[FUTUREYEAR]['rebased']))
    tasmaxs = np.stack([weathers[p][FUTUREYEAR] for p in CLIMATE_VARIABLES])
    ybar_future = cal_proj(tasmax=tasmaxs,
                           gammas=gammas_lowrisk,
                           belowzero=belowzero_lowrisk)
    yrebase = np.mean(ybar_future) - basevals_bar_lowrisk
    print('\t Calculated: %.12g' % yrebase)
    lib.show_header("Rebased, highrisk future result (%.12g reported)" % (outputs_highrisk[FUTUREYEAR]['rebased']))
    ybar_future = cal_proj(tasmax=tasmaxs,
                           gammas=gammas_highrisk,
                           belowzero=belowzero_highrisk)
    yrebase = np.mean(ybar_future) - basevals_bar_highrisk
    print('\t Calculated: %.12g' % yrebase)


if __name__ == '__main__':
    import sys

    main(projout_dir=sys.argv[1])
