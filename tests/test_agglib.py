import pytest
from generate import agglib
from generate import aggregate
import copy 
import collections

def test_interpret_costs_use_args():

	"""
	testing the behavior of agglib.interpret_cost_use_args()
	"""

	# a simple case requesting two use_args 
	assert agglib.interpret_costs_use_args(['clim_scenario', 'rcp_num'], '','','','rcp85','','','','','')[0]=='rcp85'
	# switch order and verify the output changes accordingly
	assert agglib.interpret_costs_use_args(['rcp_num', 'clim_scenario'], '','','','rcp85','','','','','')[1]=='rcp85'
	# verify the numeric-style scenarios are properly workings
	assert agglib.interpret_costs_use_args(['rcp_num', 'clim_scenario'], '','','','rcp85','','','','','')[0]=='85'
	# check seed reading works 
	assert agglib.interpret_costs_use_args(['seed-csvv'],
	 'tests/testdata/agsingle',
	 'single','','rcp85','','','','cassava-031020.nc4', 'somesuf')[0]=='1603562142'

def test_interpret_costs_args():

	'''
	testing the behavior of agglib.interpret_cost_args()
	'''
	templates = {'outputdir':'/shares/gcp/outputs/agriculture/impacts-mealy/testing/montecarlo-cassava-261020/montecarlo', 
	'targetdir' : 'batch7/rcp45/surrogate_CanESM2_89/high/SSP3',
	'filename' : 'cassava-031020.nc4',
	'batch':'batch7',
	'clim_scenario':'rcp45',
	'clim_model':'rcp85',
	'econ_model':'high',
	'econ_scenario':'SSP3',
	'costs_suffix':'somesuf'}

	# standard behavior 
	strd = agglib.interpret_costs_args(costs_config={'ordered-args': {'extra-args': ['extraarg1', 'extraarg2'],
	                                  'use-args': ['rcp_num', 'clim_scenario']}, 'costs-suffix':'somesuf'},
	                                  **templates)

	assert len(strd)==4
	assert strd[0]=='extraarg1'
	assert strd[3]=='rcp45'

	# switch the order of use-args and extra-args and verify output changes accordingly 
	revert1 = agglib.interpret_costs_args(costs_config={'ordered-args': collections.OrderedDict({'use-args': ['rcp_num', 'clim_scenario'],
                                  'extra-args': ['extraarg1','extraarg2']}),'costs-suffix':'somesuf'}, 
                                  **templates)

	assert revert1[0]=='45'
	assert revert1[3]=='extraarg2'

	# flip the order within use-args an extra-args and verify output changes accordingly
	revert2 = agglib.interpret_costs_args(costs_config={'ordered-args': collections.OrderedDict({'use-args': ['clim_scenario', 'rcp_num'],
                                  'extra-args': ['extraarg2','extraarg1']}), 'costs-suffix':'somesuf'}, 
                                  **templates)

	assert revert2[0]=='rcp45'
	assert revert2[3]=='extraarg1'

	# verify that a ValueError is raised if use-args and extra-args are missing from ordered-args
	with pytest.raises(ValueError):
		agglib.interpret_costs_args(costs_config={'ordered-args':collections.OrderedDict({'random-args':'idk'}), 'costs-suffix':'somesuf'})

def test_fullfile():

	# with suffix starting with '-' and infix in the config
	assert aggregate.fullfile('myname.nc4', '-another-suffix', {'infix':'onesuffix'})=='myname-onesuffix-another-suffix.nc4'
	# with suffix not starting with '-' and without infix in config -- verify the suffix becomes the full name.  
	assert aggregate.fullfile('myname.nc4', 'newname', {})=='newname.nc4'

def test_interpret_costs_config():

	'''
	testing the behavior of agglib.interpret_costs_config(). Mainly, verifying 
	that correct calls return arguments in the order indicated in the spec and 
	verifying that the function does its main job which it to raise ValueError if 
	key elements are missing from the config. 

	'''

	# correct config template to be deep-copied and modified at every test step 
	nice_config = {
		'outputdir': '/shares/gcp/outputs/agriculture/impacts-mealy/testing/rice-single-191020',
		'targetdir': '/shares/gcp/outputs/agriculture/impacts-mealy/testing/rice-single-191020/single/rcp85/CCSM4/high/SSP3',
		'aggregate-weighting': 'constcsv/estimation/agriculture/Data/1_raw/3_cropped_area/agglomerated-world-new-hierid-crop-weights.csv:hierid:rice',
		'basename': 'rice-191020',
		'costs-config': { 
			'command-prefix': 'Rscript /home/etenezakis/CIL_repo/agriculture/1_code/3_projections/4_run_projections/adaptation_costs/tmp_and_prcp_costs.R',
			'ordered-args': collections.OrderedDict({
				'extra-args': ['rice', 13,'""'],
	    		'use-args': ['batchwd','clim_model','rcp_num','ssp_num','iam']
	    	}),
	    	'costs-suffix': 'adaptation_costs',
			'check-variable-costs': 'adpt.cost.cuml',
		}
	}

	# verifying that it properly returns the config elements 
	work_config = copy.deepcopy(nice_config.get('costs-config'))
	assert agglib.interpret_costs_config(costs_config=work_config)[0]=='Rscript /home/etenezakis/CIL_repo/agriculture/1_code/3_projections/4_run_projections/adaptation_costs/tmp_and_prcp_costs.R'
	assert agglib.interpret_costs_config(costs_config=work_config)[4]=='adaptation_costs'
	assert agglib.interpret_costs_config(costs_config=work_config)[5]=='adpt.cost.cuml'
	assert len(agglib.interpret_costs_config(costs_config=work_config))==6

	# in all that follows, dropping various key elements and verifying Exceptions are raised 
	work_config = copy.deepcopy(nice_config.get('costs-config'))
	work_config.pop('command-prefix')
	with pytest.raises(ValueError):
		agglib.interpret_costs_config(costs_config=work_config)

	work_config = copy.deepcopy(nice_config.get('costs-config'))
	work_config.pop('ordered-args')
	with pytest.raises(ValueError):
		agglib.interpret_costs_config(costs_config=work_config)

	work_config = copy.deepcopy(nice_config.get('costs-config'))
	work_config['ordered-args'].pop('extra-args')
	assert agglib.interpret_costs_config(costs_config=work_config)[3]==None

	work_config = copy.deepcopy(nice_config.get('costs-config'))
	work_config['ordered-args'].pop('extra-args')
	work_config['ordered-args'].pop('use-args')
	with pytest.raises(ValueError):
		agglib.interpret_costs_config(costs_config=work_config)

	work_config = copy.deepcopy(nice_config.get('costs-config'))
	work_config['ordered-args']['extra-args'] = {}
	work_config['ordered-args']['use-args'] = {}
	with pytest.raises(ValueError):
		agglib.interpret_costs_config(costs_config=work_config)

	work_config = copy.deepcopy(nice_config.get('costs-config'))
	work_config['meta-info'] = {}
	with pytest.raises(ValueError):
		agglib.interpret_costs_config(costs_config=work_config)
