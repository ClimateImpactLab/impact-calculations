import pytest
from generate import agglib

def test_interpret_cost_args():

    assert agglib.interpret_cost_args(['clim_scenario', 'rcp_int'], 'whatever','/idontknow/rcp85/idk/idk/end','idk')[0]=='rcp85'
    assert agglib.interpret_cost_args(['rcp_int', 'clim_scenario'], 'whatever','/idontknow/rcp85/idk/idk/end','idk')[1]=='rcp85'
    assert agglib.interpret_cost_args(['seed-csvv'],
     '/shares/gcp/outputs/agriculture/impacts-mealy/testing/montecarlo-cassava-261020/montecarlo',
     'batch7/rcp45/surrogate_CanESM2_89/high/SSP3','cassava-031020.nc4')[0]==1603562142


@pytest.mark.imperics_shareddir
def test_get_monthbin_index():
    """
    testing strategy : splitting input
        - crop:wheat-winter, region:FRA.41.57, plant_month:10, harvest_month:8 ( => rolling years )

            - len(monthbin)==1 (=> no binning), len(monthbin)==2 (=> two bins), len(monthbin)==3 (=> three bins)
            - len(monthbin)==1 & (subseason=None, subseason='fall', subseason='winter')
            - clim_var = '...1', clim_var= '...2'


        - crop:rice, region:FRA.83.63, plant_month:5, harvest_month:10 ( => unique year )

            - len(monthbin)==4 ( => four bins)
            - clim_var = '...1', clim_var= '...4'


    -
    """
    culture_periods = irvalues.get_file_cached('social/baselines/agriculture/world-combo-202004-growing-seasons-wheat-winter.csv', irvalues.load_culture_months)
    clim_var='somename_1'
    assert seasonal_climategen.get_monthbin_index('FRA.41.57', culture_periods, clim_var, [24])==(10-1,12+8-1+1)
    assert seasonal_climategen.get_monthbin_index('FRA.41.57', culture_periods, clim_var, [24], subseason='fall', suffix_triangle=get_test_suffix_triangle())==(10-1,11-1+1)
    assert seasonal_climategen.get_monthbin_index('FRA.41.57', culture_periods, clim_var, [24], subseason='winter', suffix_triangle=get_test_suffix_triangle())==(12-1, (3+12)-1+1)
    assert seasonal_climategen.get_monthbin_index('FRA.41.57', culture_periods, clim_var, [1, 24-1])==(10-1,10-1+1)
    assert seasonal_climategen.get_monthbin_index('FRA.41.57', culture_periods, clim_var, [3,4,24-3-4])==(10-1,12-1+1)
    clim_var='somename_2'
    assert seasonal_climategen.get_monthbin_index('FRA.41.57', culture_periods, clim_var, [1, 24-1])==(11-1,12+8-1+1)
    assert seasonal_climategen.get_monthbin_index('FRA.41.57', culture_periods, clim_var, [3,4,24-3-4])==(12+1-1,12+4-1+1)
    culture_periods = irvalues.get_file_cached('social/baselines/agriculture/world-combo-201710-growing-seasons-rice-1stseason.csv', irvalues.load_culture_months)
    clim_var='somename_1'
    assert seasonal_climategen.get_monthbin_index('FRA.83.63', culture_periods, clim_var, [1,1,2,24-1-1-2])==(5-1,5+1-1)
    clim_var='somename_4'
    assert seasonal_climategen.get_monthbin_index('FRA.83.63', culture_periods, clim_var, [1,1,2,24-1-1-2])==(9-1, 10-1+1)

@pytest.mark.imperics_shareddir
def test_get_monthbin_index_fail_badvarstructure():
    """
    should fail because variable name indicates second bin and there's only one in the vector
    """
    with pytest.raises(AssertionError):
        culture_periods = irvalues.get_file_cached('social/baselines/agriculture/world-combo-202004-growing-seasons-wheat-winter.csv', irvalues.load_culture_months)
        clim_var='somename_2'
        seasonal_climategen.get_monthbin_index('FRA.41.57', culture_periods, clim_var, [24])

@pytest.mark.imperics_shareddir
def test_get_monthbin_index_fail_toolongtime():
    """
    should fail because vector sum is above 24
    """
    with pytest.raises(AssertionError):
        culture_periods = irvalues.get_file_cached('social/baselines/agriculture/world-combo-201710-growing-seasons-rice-1stseason.csv', irvalues.load_culture_months)
        clim_var='somename_4'
        seasonal_climategen.get_monthbin_index('FRA.83.63', culture_periods, clim_var, [20, 30, 40, 20])


@pytest.mark.imperics_shareddir
def test_get_monthbin_index_fail_badvarname():
    """
    should fail with a value error because the var name's last letter doesn't indicate a bin, and the code tries to coerce an alphabetic character to an integer.
    """
    with pytest.raises(ValueError):
        culture_periods = irvalues.get_file_cached('social/baselines/agriculture/world-combo-201710-growing-seasons-rice-1stseason.csv', irvalues.load_culture_months)
        clim_var='somebadname'
        seasonal_climategen.get_monthbin_index('FRA.83.63', culture_periods, clim_var, [24])

@pytest.mark.imperics_shareddir
def test_is_longrun_climate():
    assert seasonal_climategen.is_longrun_climate('seasonaledd') == False
    assert seasonal_climategen.is_longrun_climate('seasonaltasmax') == True
