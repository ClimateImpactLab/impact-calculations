from generate import seasonal_climategen
from datastore import irvalues

non_leap_year = 2010

def test_get_seasonal_index():

	"""
	testing strategy : splitting input

	- - crop:rice
		- region:'ZWE.8.43',plant_month:11, harvest_month:5
		- region:'ZWE.8.43',plant_month:11, harvest_month:5, transform_index:False
		- region:'FRA.83.63', plant_month:5, harvest_month:10
		- region:'FRA.83.63', plant_month:5, harvest_month:10, subseason:'summer'
		- region:'FRA.83.63', plant_month:5, harvest_month:10, subseason:'winter'
		- region:'FRA.73.82', plant_month:2, harvest_month:9, subseason:'fall'
		- region:'ASM.Ra9b78739fcd43737', plant_month:1, harvest_month:6, subseason:'summer'
		- region:'ASM.Ra9b78739fcd43737', plant_month:1, harvest_month:6, subseason:'fall'

	- crop:wheat-winter 
		- region:GRC.13.R0cbc533353135881,plant_month:11, harvest_month:6, subseason:'summer'
		- region:GRC.13.R0cbc533353135881,plant_month:11, harvest_month:6, subseason:'fall'
		- region:FRA.41.57, plant_month=10, harvest_month=8 & subseason:'winter'

	"""

	culture_periods = irvalues.get_file_cached('social/baselines/agriculture/world-combo-201710-growing-seasons-rice-1stseason.csv', irvalues.load_culture_months)
	assert seasonal_climategen.get_seasonal_index('ZWE.8.43', culture_periods) == (11-1, (5+12)-1+1) #rolling years entire growing season
	assert seasonal_climategen.get_seasonal_index('ZWE.8.43', culture_periods, transform_index=False) == (11, (5+12)) #rolling years entire growing season
	assert seasonal_climategen.get_seasonal_index('FRA.83.63', culture_periods) == (5-1, 10-1+1) #single year entire growing season
	assert seasonal_climategen.get_seasonal_index('FRA.83.63', culture_periods, 'summer', seasonal_climategen.get_suffix_triangle()) == (6-1, 10+1-1) #just the summer
	assert seasonal_climategen.get_seasonal_index('FRA.83.63', culture_periods, 'fall', seasonal_climategen.get_suffix_triangle()) == (5-1, 5+1-1) #just the fall
	assert seasonal_climategen.get_seasonal_index('FRA.83.63', culture_periods, 'winter', seasonal_climategen.get_suffix_triangle()) == (None, None) #just the winter that 'doesn't exist'
	assert seasonal_climategen.get_seasonal_index('FRA.73.82', culture_periods, 'fall', seasonal_climategen.get_suffix_triangle()) == (2-1,3+1-1) #just fall, another example
	assert seasonal_climategen.get_seasonal_index('FRA.73.82', culture_periods, 'winter', seasonal_climategen.get_suffix_triangle()) == (4-1,4+1-1) #just winter, yet another example
	assert seasonal_climategen.get_seasonal_index('ASM.Ra9b78739fcd43737', culture_periods, 'summer', seasonal_climategen.get_suffix_triangle()) == (2-1,6+1-1) #boundary case (starts at first month)
	assert seasonal_climategen.get_seasonal_index('ASM.Ra9b78739fcd43737', culture_periods, 'fall', seasonal_climategen.get_suffix_triangle()) == (1-1,1+1-1) #idem


	culture_periods = irvalues.get_file_cached('social/baselines/agriculture/world-combo-202004-growing-seasons-wheat-winter.csv', irvalues.load_culture_months)
	assert seasonal_climategen.get_seasonal_index('GRC.13.R0cbc533353135881', culture_periods, 'summer', seasonal_climategen.get_suffix_triangle()) == ((2+12)-1, (6+12)-1+1) #rolling year + just the 'summer'
	assert seasonal_climategen.get_seasonal_index('GRC.13.R0cbc533353135881', culture_periods, 'fall', seasonal_climategen.get_suffix_triangle()) == (11-1, 12-1+1) #just the fall
	assert seasonal_climategen.get_seasonal_index('FRA.41.57', culture_periods, 'winter', seasonal_climategen.get_suffix_triangle()) == (12-1, (3+12)-1+1) #just the winter that 'doesn't exist'


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
	assert seasonal_climategen.get_monthbin_index('FRA.41.57', culture_periods, clim_var, [24], subseason='fall', suffix_triangle=seasonal_climategen.get_suffix_triangle())==(10-1,11-1+1)
	assert seasonal_climategen.get_monthbin_index('FRA.41.57', culture_periods, clim_var, [24], subseason='winter', suffix_triangle=seasonal_climategen.get_suffix_triangle())==(12-1, (3+12)-1+1)
	assert seasonal_climategen.get_monthbin_index('FRA.41.57', culture_periods, clim_var, [1, 24-1])==(10-1,10-1+1)
	assert seasonal_climategen.get_monthbin_index('FRA.41.57', culture_periods, clim_var, [3,4,24-3-4])==(10-1,12-1+1)
	clim_var='somename_2'
	try:
		seasonal_climategen.get_monthbin_index('FRA.41.57', culture_periods, clim_var, [24])
	except:
		print('failing as expected')
		pass
	assert seasonal_climategen.get_monthbin_index('FRA.41.57', culture_periods, clim_var, [1, 24-1])==(11-1,12+8-1+1)
	assert seasonal_climategen.get_monthbin_index('FRA.41.57', culture_periods, clim_var, [3,4,24-3-4])==(12+1-1,12+4-1+1)





	culture_periods = irvalues.get_file_cached('social/baselines/agriculture/world-combo-201710-growing-seasons-rice-1stseason.csv', irvalues.load_culture_months)
	clim_var='somename_1'
	assert seasonal_climategen.get_monthbin_index('FRA.83.63', culture_periods, clim_var, [1,1,2,24-1-1-2])==(5-1,5+1-1)
	clim_var='somename_4'
	assert seasonal_climategen.get_monthbin_index('FRA.83.63', culture_periods, clim_var, [1,1,2,24-1-1-2])==(9-1, 10-1+1)
	try:
		seasonal_climategen.get_monthbin_index('FRA.83.63', culture_periods, clim_var, [20, 30, 40, 20])
	except:
		print('failing as expected')
		pass
	clim_var='somebadname'
	try:
		seasonal_climategen.get_monthbin_index('FRA.83.63', culture_periods, clim_var, [24])
	except:	
		print('failing as expected')
		pass


if __name__ == '__main__':
	test_get_seasonal_index()
	test_get_monthbin_index()
