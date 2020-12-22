from generate import seasonal_climategen
from datastore import irvalues

non_leap_year = 2010

def test_get_seasonal_index():

	"""
	testing strategy : splitting input the following way :

	- rice
		- region=='ZWE.8.43' : plant_month==11, harvest_month==5
		- region=='FRA.83.63' => plant_month==5, harvest_month==10
		- region=='FRA.83.63' => plant_month==5, harvest_month==10 & subseason=='summer'
		- region=='FRA.83.63' => plant_month==5, harvest_month==10 & subseason=='winter'
		- region=='FRA.73.82': plant_month==2, harvest_month==9 & subseason=='fall'
		- region=='ASM.Ra9b78739fcd43737': plant_month==1, harvest_month==6 & subseason=='summer'
		- region=='ASM.Ra9b78739fcd43737': plant_month==1, harvest_month==6 & subseason=='fall'

	- wheat 
		- region==GRC.13.R0cbc533353135881 : plant_month==11, harvest_month==6 & subseason=='summer'
		- region==GRC.13.R0cbc533353135881 : plant_month==11, harvest_month==6 & subseason=='fall'
		- region==FRA.41.57: plant_month=10, harvest_month=8 & subseason=='winter'

	"""

	culture_periods = irvalues.get_file_cached('social/baselines/agriculture/world-combo-201710-growing-seasons-rice-1stseason.csv', irvalues.load_culture_months)
	print(culture_periods['AUS.6.701'])
	assert seasonal_climategen.get_seasonal_index('ZWE.8.43', culture_periods) == (11-1, (5+12)-1+1) #rolling years entire growing season
	assert seasonal_climategen.get_seasonal_index('FRA.83.63', culture_periods) == (5-1, 10-1+1) #single year entire growing season
	assert seasonal_climategen.get_seasonal_index('FRA.83.63', culture_periods, 'summer', seasonal_climategen.get_suffix_triangle()) == (6-1, 10+1-1) #just the summer
	assert seasonal_climategen.get_seasonal_index('FRA.83.63', culture_periods, 'fall', seasonal_climategen.get_suffix_triangle()) == (5-1, 5+1-1) #just the fall
	assert seasonal_climategen.get_seasonal_index('FRA.83.63', culture_periods, 'winter', seasonal_climategen.get_suffix_triangle()) == (None, None) #just the winter that 'doesn't exist'
	assert seasonal_climategen.get_seasonal_index('FRA.73.82', culture_periods, 'fall', seasonal_climategen.get_suffix_triangle()) == (2-1,3+1-1) #just fall, another example
	assert seasonal_climategen.get_seasonal_index('FRA.73.82', culture_periods, 'winter', seasonal_climategen.get_suffix_triangle()) == (4-1,4+1-1) #just winter, yet another example
	assert seasonal_climategen.get_seasonal_index('ASM.Ra9b78739fcd43737', culture_periods, 'summer', seasonal_climategen.get_suffix_triangle()) == (2-1,6+1-1) #boundary case (starts at first month)
	assert seasonal_climategen.get_seasonal_index('ASM.Ra9b78739fcd43737', culture_periods, 'fall', seasonal_climategen.get_suffix_triangle()) == (1-1,1+1-1) #idem


	culture_periods = irvalues.get_file_cached('social/baselines/agriculture/world-combo-202004-growing-seasons-wheat-winter.csv', irvalues.load_culture_months)
	print(culture_periods['KAZ.2.R38bf44355c9fae16'])
	assert seasonal_climategen.get_seasonal_index('GRC.13.R0cbc533353135881', culture_periods, 'summer', seasonal_climategen.get_suffix_triangle()) == ((2+12)-1, (6+12)-1+1) #rolling year + just the 'summer'
	assert seasonal_climategen.get_seasonal_index('GRC.13.R0cbc533353135881', culture_periods, 'fall', seasonal_climategen.get_suffix_triangle()) == (11-1, 12-1+1) #just the fall
	assert seasonal_climategen.get_seasonal_index('FRA.41.57', culture_periods, 'winter', seasonal_climategen.get_suffix_triangle()) == (12-1, (3+12)-1+1) #just the winter that 'doesn't exist'


	
test_get_seasonal_index()
