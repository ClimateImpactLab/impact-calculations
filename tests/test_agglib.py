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