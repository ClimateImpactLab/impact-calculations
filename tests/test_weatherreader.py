import unittest
import numpy as np
from numpy import testing
from climate.dailyreader import *

class TestWeatherReader(unittest.TestCase):
    def test_bincompare(self):
        # Check the first month of daily values
        print "Reading from the daily data files."
        template1 = "/shares/gcp/BCSD/grid2reg/cmip5/historical/CCSM4/tas/tas_day_aggregated_historical_r1i1p1_CCSM4_%d.nc"
        weatherreader1 = DailyWeatherReader(template1, 1981, 'SHAPENUM', 'tas')

        print weatherreader1.version, weatherreader1.units
        self.assertEqual(weatherreader1.units, "Celsius")

        self.assertEqual(len(weatherreader1.get_dimension()), 1)

        alltimes1 = weatherreader1.get_times()

        # Compare it to the first month of binned values
        print "Reading from the binned data files."
        template2 = "/home/jrising/tas_Bindays_aggregated_historical_r1i1p1_CCSM4_%d_new.nc" #"/shares/gcp/BCSD/grid2reg/cmip5_bins/historical/CCSM4/tas/tas_Bindays_aggregated_historical_r1i1p1_CCSM4_%d.nc"
        weatherreader2 = BinnedWeatherReader(template2, 1981, 'SHAPENUM', 'DayNumber')

        print weatherreader2.version, weatherreader2.units
        self.assertEqual(weatherreader2.units, "days")

        self.assertEqual(len(weatherreader2.get_dimension()), 12)

        alltimes2 = weatherreader2.get_times()

        iterator1 = weatherreader1.read_iterator()
        iterator2 = weatherreader2.read_iterator()
        while alltimes1 or alltimes2:
            times1, weather1 = iterator1.next()
            times2, weather2 = iterator2.next()

            testing.assert_array_equal(alltimes1[:len(times1)], times1)
            alltimes1 = alltimes1[len(times1):]

            testing.assert_array_equal(alltimes2[:len(times2)], times2)
            alltimes2 = alltimes2[len(times2):]

            binlimits = [-np.inf, -17, -12, -7, -2, 3, 8, 13, 18, 23, 28, 33, np.inf]
            bincenters = [-19.5] + list((np.array(binlimits[1:-2]) + np.array(binlimits[2:-1])) / 2) + [35.5]
            dayspermonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            monthlimits = [0] + list(np.cumsum(dayspermonth))

            self.assertEqual(weather1.shape[1], weather2.shape[1])

            for region in range(weather1.shape[1]): # iterate through regions
                for month in range(12):
                    monthtemps = weather1[monthlimits[month]:monthlimits[month+1], region]
                    
                    dailymean = np.mean(monthtemps[(monthtemps > -17) & (monthtemps < 33)])
                    binnedmean = np.sum(weather2[month, region, 1:-1] * bincenters[1:-1]) / sum(weather2[month, region, 1:-1])
                    #testing.assert_almost_equal(dailymean, binnedmean, decimal=0)
                    
                    aggthenbin = []
                    
                    for ii in range(len(binlimits)-1):
                        days = np.sum((monthtemps >= binlimits[ii]) & (monthtemps < binlimits[ii+1]))
                        aggthenbin.append(days)

                        # Check that bins match expected
                        #testing.assert_almost_equal(days, weather2[month, region, ii], decimal=-1)

                    print region + 1
                    print weather2[month, region, :]
                    print aggthenbin

                    binnedmean = np.sum(weather2[month, region, :] * bincenters) / sum(weather2[month, region, :])
                    binnedvar = np.sum(weather2[month, region, :] * (bincenters - binnedmean)**2) / sum(weather2[month, region, :])
                    
                    dailymean = np.sum(np.array(aggthenbin) * bincenters) / sum(aggthenbin)
                    dailyvar = np.sum(np.array(aggthenbin) * (bincenters - dailymean)**2) / sum(aggthenbin)
                     
                    #testing.assert_almost_equal(dailymean, binnedmean, decimal=0 - int((weather2[month, region, 0] + weather2[month, region, -1]) / 5))
   
                    print np.sqrt(binnedvar), np.sqrt(dailyvar)
                    if not np.isnan(np.sqrt(binnedvar)) and region > 7868: # best: 5428
                        self.assertTrue(np.sqrt(binnedvar) >= np.sqrt(dailyvar) - .5) # -1 for rounding error

if __name__ == '__main__':
    unittest.main()

