from generate import seasonal_climategen
from datastore import irvalues

non_leap_year = 2010

def test_get_seasonal_index():

	"""
	testing strategy : splitting input the following way :
	- region=='ZWE.8.43' : plant_month==11, harvest_month==5
	- region=='FRA.83.63' => plant_month==5, harvest_month==10
	- region=='FRA.83.63' => plant_month==5, harvest_month==10 & subseason=='summer'
	- region=='FRA.83.63' => plant_month==5, harvest_month==10 & subseason=='winter'
	- region=='FRA.73.82': plant_month==2, harvest_month==9 & subseason=='fall'
	- region=='ASM.Ra9b78739fcd43737': plant_month==1, harvest_month==6 & subseason=='summer'
	- region=='ASM.Ra9b78739fcd43737': plant_month==1, harvest_month==6 & subseason=='fall'


	"""

	culture_periods = irvalues.get_file_cached('social/baselines/agriculture/world-combo-201710-growing-seasons-rice-1stseason.csv', irvalues.load_culture_months)
	assert seasonal_climategen.get_seasonal_index('ZWE.8.43', culture_periods) == (10, 5+12) #rolling years entire growing season
	assert seasonal_climategen.get_seasonal_index('FRA.83.63', culture_periods) == (4, 10) #single year entire growing season
	assert seasonal_climategen.get_seasonal_index('FRA.83.63', culture_periods, 'summer') == (6, 10) #just the summer
	assert seasonal_climategen.get_seasonal_index('FRA.83.63', culture_periods, 'fall') == (4, 5) #just the fall
	assert seasonal_climategen.get_seasonal_index('FRA.83.63', culture_periods, 'winter') == (None, None) #just the winter that 'doesn't exist'
	assert seasonal_climategen.get_seasonal_index('FRA.73.82', culture_periods, 'fall') == (1,2) #just fall, another example
	assert seasonal_climategen.get_seasonal_index('FRA.73.82', culture_periods, 'winter') == (3,4) #just winter, yet another example
	assert seasonal_climategen.get_seasonal_index('ASM.Ra9b78739fcd43737', culture_periods, 'summer') == (2,6) #boundary case (starts at first month)
	assert seasonal_climategen.get_seasonal_index('ASM.Ra9b78739fcd43737', culture_periods, 'fall') == (0,1) #idem


	# #GRC.13.R0cbc533353135881 : plant_month==11, harvest_month==6 & subseason=='summer'
	# #GRC.13.R0cbc533353135881 : plant_month==11, harvest_month==6 & subseason=='fall'
	# #FRA.41.57 : plant_month=10, harvest_month=8 & subseason=='winter'

	# culture_periods = irvalues.get_file_cached('social/baselines/agriculture/world-combo-202004-growing-seasons-wheat-winter.csv', irvalues.load_culture_months)
	# assert seasonal_climategen.get_seasonal_index('GRC.13.R0cbc533353135881', culture_periods, 'summer') == (12+2, 12+6) #rolling year + just the 'summer'
	# assert seasonal_climategen.get_seasonal_index('GRC.13.R0cbc533353135881', culture_periods, 'fall') == (10, 11) #just the fall
	# assert seasonal_climategen.get_seasonal_index('FRA.41.57', culture_periods, 'winter') == (None, None) #just the winter that 'doesn't exist'


	
test_get_seasonal_index()
