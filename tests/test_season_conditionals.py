"""Try different representations of conditional month-of-season coefficients.

All of these models are based on the core maize model and the
precipitation polynomial, which was had the original form of the
month-of-season processing.

"""

import pytest
import yaml, copy
import numpy as np
from impactlab_tools.utils import files
from adaptation import csvvfile
from interpret import container
from generate import loadmodels, pvalses, caller, effectset

master_config = """
timerate: month
grid-weight: cropwt
rolling-years: 2
climate: [ tasmax, edd, pr, pr-poly-2 = pr-monthsum-poly-2 ]
models:
  - csvvs: "social/parameters/agriculture/corn/corn_global_t-pbar_spline_gdd-200mm_kdd-100mm_tbar_lnincbr_ir_tp_binp-tbar_pbar_spline_prcp-250mm_lnincbr_ir_tp_fe-A1TT_A0Y_clus-A1_A0Y_TINV-200316.csvv"
    within-season: "social/baselines/agriculture/world-combo-201710-growing-seasons-corn-1stseason.csv"
    clipping: false
    covariates:
      - loggdppc
      - seasonaltasmax
      - seasonalpr
      - ir-share
      - seasonaltasmax*seasonalpr
      - seasonalprspline: [100, 200, 250]
      - seasonaltasmax*seasonalprspline: [100, 200, 250]
    description: Yield rate for corn
    specifications:
      gddkdd:
        functionalform: coefficients
        description: Temperature-driven yield rate for corn
        depenunit: log kg / Ha
        variables:
          gdd-8-31: edd.bin(8) - edd.bin(31) [C day]
          kdd-31: edd.bin(31) [C day]
        beta-limits:
          kdd-31: -inf, 0
      precip:
        functionalform: sum-by-time
        description: Precipitation-driven yield rate for corn
        depenunit: log kg / Ha
        indepunit: mm
        suffixes: [1, 2, 3, 4, 5, 6, 7, 8, 9, r, r, r]
        subspec:
          variable: pr
          functionalform: polynomial 
    calculation:
      - Sum:
        - YearlySumIrregular:
            model: gddkdd
        - YearlySumIrregular:
            model: precip
      - Rebase
      - KeepOnly:
        - rebased
"""

def modify_config_triangle(config):
    json_str = """
      - [1]
      - [1, 2]
      - [1, 2, 3]
      - [1, 2, 3, 4]
      - [1, 2, 3, 4, 5]
      - [1, 2, 3, 4, 5, 6]
      - [1, 2, 3, 4, 5, 6, 7]
      - [1, 2, 3, 4, 5, 6, 7, 8]
      - [1, 2, 3, 4, 5, 6, 7, 8, 9]
      - [1, 2, 3, 4, 5, 6, 7, 8, 9, r]
      - [1, 2, 3, 4, 5, 6, 7, 8, 9, r, r]
      - [1, 2, 3, 4, 5, 6, 7, 8, 9, r, r, r]
    """

    config = copy.deepcopy(config)
    del config['models'][0]['specifications']['precip']['suffixes']
    config['models'][0]['specifications']['precip']['suffix-triangle'] = yaml.load(json_str)
    return config

def modify_config_condition(config):
    json_str = """
        - YearlySumIrregular:
            model: gddkdd
        - YearlySumIrregular:
            model: precip1
        - YearlySumIrregular:
            model: precip2
    """
    
    config = copy.deepcopy(config)
    
    precip_config = config['models'][0]['specifications'].pop('precip')
    precip1_config = copy.deepcopy(precip_config)
    precip1_config['suffixes'] = [1, 2, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    precip2_config = copy.deepcopy(precip_config)
    precip2_config['suffixes'] = [0, 0, 0, 4, 5, 6, 7, 8, 9, 'r', 'r', 'r']
    
    config['models'][0]['specifications']['precip1'] = precip1_config
    config['models'][0]['specifications']['precip2'] = precip2_config
    config['models'][0]['calculation'][0]['Sum'] = yaml.load(json_str)
    return config

module = 'interpret.calcspec'

@pytest.fixture
def setup():
    """Run projection with default config and save elements."""
    config = yaml.load(master_config)

    container.preload()

    clim_scenario, clim_model, weatherbundle, econ_scenario, econ_model, economicmodel = loadmodels.single(container.get_bundle_iterator(config))
    pvals = pvalses.ConstantPvals(.5)
    csvv = csvvfile.read(files.configpath(config['models'][0]['csvvs']))
    
    calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(csvv, module, weatherbundle, economicmodel, pvals["full"], specconf=config['models'][0], config=config, standard=False)
    outputs_master = effectset.small_print(weatherbundle, calculation, ['USA.14.608'])

    return dict(config=config, weatherbundle=weatherbundle, economicmodel=economicmodel, pvals=pvals, csvv=csvv, outputs=outputs_master)

@pytest.mark.imperics_shareddir
def test_triangle(setup):
    """Try to use a triangle suffixes config equivalent to the list suffixes."""
    config_triangle = modify_config_triangle(setup['config'])
    weatherbundle = setup['weatherbundle']
    economicmodel = setup['economicmodel']
    pvals = setup['pvals']
    csvv = setup['csvv']

    calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(csvv, module, weatherbundle, economicmodel, pvals["full"], specconf=config_triangle['models'][0], config=config_triangle, standard=False)
    outputs_triangle = effectset.small_print(weatherbundle, calculation, ['USA.14.608'])

    np.testing.assert_array_almost_equal(setup['outputs'], outputs_triangle)

@pytest.mark.imperics_shareddir
def test_condition(setup):
    """Try to use two predictors conditionally, equivalent to the single predictor."""
    config_condition = modify_config_condition(setup['config'])
    weatherbundle = setup['weatherbundle']
    economicmodel = setup['economicmodel']
    pvals = setup['pvals']
    csvv = setup['csvv']

    calculation, dependencies, baseline_get_predictors = caller.call_prepare_interp(csvv, module, weatherbundle, economicmodel, pvals["full"], specconf=config_condition['models'][0], config=config_condition, standard=False)
    outputs_condition = effectset.small_print(weatherbundle, calculation, ['USA.14.608'])

    np.testing.assert_array_almost_equal(setup['outputs'], outputs_condition)

