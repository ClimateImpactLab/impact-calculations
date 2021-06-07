import pytest
from generate import agglib
from generate import aggregate
import copy 

@pytest.mark.imperics_shareddir
def test_interpret_cost_use_args():

    assert agglib.interpret_cost_use_args(['clim_scenario', 'rcp_num'], '','','','rcp85','','','','','')[0]=='rcp85'
    # check order preserved
    assert agglib.interpret_cost_use_args(['rcp_num', 'clim_scenario'], '','','','rcp85','','','','','')[1]=='rcp85'
    # check int works
    assert agglib.interpret_cost_use_args(['rcp_num', 'clim_scenario'], '','','','rcp85','','','','','')[0]=='85'
    # check seed reading works 
    assert agglib.interpret_cost_use_args(['seed-csvv'],
     '/shares/gcp/outputs/agriculture/impacts-mealy/testing/montecarlo-cassava-261020/montecarlo',
     'batch7/rcp45/surrogate_CanESM2_89/high/SSP3','','rcp85','','','','cassava-031020.nc4', 'somesuf')[0]=='1603562142'

@pytest.mark.imperics_shareddir
def test_interpret_cost_args():

	templates = {'outputdir':'/shares/gcp/outputs/agriculture/impacts-mealy/testing/montecarlo-cassava-261020/montecarlo', 
	'targetdir' : 'batch7/rcp45/surrogate_CanESM2_89/high/SSP3',
	'filename' : 'cassava-031020.nc4',
	'batch':'batch7',
	'clim_scenario':'rcp45',
	'clim_model':'rcp85',
	'econ_model':'high',
	'econ_scenario':'SSP3',
	'costs_suffix':'somesuf'}

	strd = agglib.interpret_cost_args(costs_script={'ordered-args': {'extra-args': {'extra-arg1': 'extraarg1', 'extra-arg2': 'extraarg2'},
	                                  'use-args': ['rcp_num', 'clim_scenario']}, 'costs-suffix':'somesuf'},
	                                  **templates)

	assert len(strd)==4
	assert strd[0]=='extraarg1'
	assert strd[3]=='rcp45'

	revert1 = agglib.interpret_cost_args(costs_script={'ordered-args': {'use-args': ['rcp_num', 'clim_scenario'],
                                  'extra-args': {'extra-arg1': 'extraarg1', 'extra-arg2': 'extraarg2'}},'costs-suffix':'somesuf'}, 
                                  **templates)

	assert revert1[0]=='45'
	assert revert1[3]=='extraarg2'

	revert2 = agglib.interpret_cost_args(costs_script={'ordered-args': {'use-args': ['clim_scenario', 'rcp_num'],
                                  'extra-args': {'extra-arg1': 'extraarg2', 'extra-arg2': 'extraarg1'}}, 'costs-suffix':'somesuf'}, 
                                  **templates)

	assert revert2[0]=='rcp45'
	assert revert2[3]=='extraarg1'

	with pytest.raises(ValueError):
		agglib.interpret_cost_args(costs_script={'ordered-args':{'random-args':'idk'}, 'costs-suffix':'somesuf'})

def test_fullfile():

	assert aggregate.fullfile('myname.nc4', '-another-suffix', {'infix':'onesuffix'})=='myname-onesuffix-another-suffix.nc4'
	assert aggregate.fullfile('myname.nc4', 'newname', {})=='newname.nc4'

def test_interpret_costs_script():

	nice_config = {
		'outputdir': '/shares/gcp/outputs/agriculture/impacts-mealy/testing/rice-single-191020',
		'targetdir': '/shares/gcp/outputs/agriculture/impacts-mealy/testing/rice-single-191020/single/rcp85/CCSM4/high/SSP3',
		'aggregate-weighting': 'constcsv/estimation/agriculture/Data/1_raw/3_cropped_area/agglomerated-world-new-hierid-crop-weights.csv:hierid:rice',
		'basename': 'rice-191020',
		'costs-script': { 
			'command-prefix': 'Rscript /home/etenezakis/CIL_repo/agriculture/1_code/3_projections/4_run_projections/adaptation_costs/tmp_and_prcp_costs.R',
			'ordered-args': {
				'extra-args': { 
					'crop': 'rice',
					'avgperiod': 13,
					'seed-csvv': '""'
				},
	    		'use-args': ['batchwd','clim_model','rcp_num','ssp_num','iam']
	    	},
	    	'costs-suffix': 'adaptation_costs',
			'check-variable-costs': 'adpt.cost.cuml',
			'description': 'yields'
		}
	}

	work_config = copy.deepcopy(nice_config.get('costs-script'))
	assert agglib.interpret_costs_script(costs_script=work_config)[0]=='Rscript /home/etenezakis/CIL_repo/agriculture/1_code/3_projections/4_run_projections/adaptation_costs/tmp_and_prcp_costs.R'
	assert agglib.interpret_costs_script(costs_script=work_config)[4]=='adaptation_costs'
	assert agglib.interpret_costs_script(costs_script=work_config)[5]=='adpt.cost.cuml'
	assert len(agglib.interpret_costs_script(costs_script=work_config))==6

	work_config = copy.deepcopy(nice_config.get('costs-script'))
	work_config.pop('command-prefix')
	with pytest.raises(ValueError):
		agglib.interpret_costs_script(costs_script=work_config)

	work_config = copy.deepcopy(nice_config.get('costs-script'))
	work_config.pop('ordered-args')
	with pytest.raises(ValueError):
		agglib.interpret_costs_script(costs_script=work_config)

	work_config = copy.deepcopy(nice_config.get('costs-script'))
	work_config['ordered-args'].pop('extra-args')
	assert agglib.interpret_costs_script(costs_script=work_config)[3]==None

	work_config = copy.deepcopy(nice_config.get('costs-script'))
	work_config['ordered-args'].pop('extra-args')
	work_config['ordered-args'].pop('use-args')
	with pytest.raises(ValueError):
		agglib.interpret_costs_script(costs_script=work_config)
