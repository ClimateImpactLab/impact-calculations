import pytest
from generate import agglib


@pytest.mark.imperics_shareddir
def test_interpret_cost_use_args():

    assert agglib.interpret_cost_use_args(['clim_scenario', 'rcp_num'], 'whatever','/idontknow/rcp85/idk/idk/end','idk')[0]=='rcp85'
    # check order preserved
    assert agglib.interpret_cost_use_args(['rcp_num', 'clim_scenario'], 'whatever','/idontknow/rcp85/idk/idk/end','idk')[1]=='rcp85'
    # check int works
    assert agglib.interpret_cost_use_args(['rcp_num', 'clim_scenario'], 'whatever','/idontknow/rcp85/idk/idk/end','idk')[0]=='85'
    # check seed reading works 
    assert agglib.interpret_cost_use_args(['seed-csvv'],
     'outputs/agriculture/impacts-mealy/testing/montecarlo-cassava-261020/montecarlo',
     'batch7/rcp45/surrogate_CanESM2_89/high/SSP3','cassava-031020.nc4')[0]==1603562142

@pytest.mark.imperics_shareddir
def test_interpret_cost_args():

	templates = {'outputdir':'outputs/agriculture/impacts-mealy/testing/montecarlo-cassava-261020/montecarlo', 
	'targetdir' : 'batch7/rcp45/surrogate_CanESM2_89/high/SSP3',
	'filename' : 'cassava-031020.nc4'}

	strd = agglib.interpret_cost_args(costs_script={'extra-args': {'extra-arg1': 'extraarg1', 'extra-arg2': 'extraarg2'},
	                                  'use-args': ['rcp_num', 'clim_scenario']}, 
	                                  outputdir=templates['outputdir'], 
	                                  targetdir=templates['targetdir'],
	                                  filename=templates['filename'])

	assert len(strd)==4
	assert strd[0]=='extraarg1'
	assert strd[3]=='rcp45'

	revert1 = agglib.interpret_cost_args(costs_script={'use-args': ['rcp_num', 'clim_scenario'],
                                  'extra-args': {'extra-arg1': 'extraarg1', 'extra-arg2': 'extraarg2'}}, 
                                  outputdir=templates['outputdir'], 
	                              targetdir=templates['targetdir'],
	                              filename=templates['filename'])

	assert revert1[0]=='45'
	assert revert1[3]=='extraarg2'

	revert2 = agglib.interpret_cost_args(costs_script={'use-args': ['clim_scenario', 'rcp_num'],
                                  'extra-args': {'extra-arg1': 'extraarg2', 'extra-arg2': 'extraarg1'}}, 
                                  outputdir=templates['outputdir'], 
	                              targetdir=templates['targetdir'],
	                              filename=templates['filename'])

	assert revert2[0]=='rcp45'
	assert revert2[3]=='extraarg1'

	with pytest.raises(ValueError):
		agglib.interpret_cost_args(costs_script={'random-args':'idk'})