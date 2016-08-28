import unittest
import numpy as np
from numpy import testing
from climate.dailyreader import *

class TestWeatherReader(unittest.TestCase):
    def test_bincompare(self):
        # Check the first month of daily values
        print "Reading from the daily data files."
        template1 = "/shares/gcp/BCSD/grid2reg/cmip5/historical/CCSM4/tas/tas_day_aggregated_historical_r1i1p1_CCSM4_%d.nc"
        weatherreader1 = DailyWeatherReader(template1, 1981, 'tas')

        print weatherreader1.version, weatherreader1.units
        self.assertEqual(weatherreader1.units, "Celsius")

        self.assertEqual(len(weatherreader1.get_dimension()), 1)

        alltimes1 = weatherreader1.get_times()

        # Compare it to the first month of binned values
        print "Reading from the binned data files."
        template2 = "/shares/gcp/BCSD/grid2reg/cmip5_bins/historical/CCSM4/tas/tas_Bindays_aggregated_historical_r1i1p1_CCSM4_%d.nc"
        weatherreader2 = BinnedWeatherReader(template2, 1981, 'DayNumber')

        print weatherreader2.version, weatherreader2.units
        self.assertEqual(weatherreader2.units, "days")

        self.assertEqual(len(weatherreader2.get_dimension()), 12)

        lltimes2 = weatherreader2.get_times()

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
            dayspermonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
            monthlimits = [0] + list(np.cumsum(dayspermonth))

            self.assertEqual(weather1.shape[1], weather2.shape[2])

            for region in range(weather1.shape[1]): # iterate through regions
                for month in range(12):
                    monthtemps = weather1[monthlimits[month]:monthlimits[month+1], region]
                    for ii in range(len(binlimits)-1):
                        days = np.sum((monthtemps >= binlimits[ii]) & (monthtemps < binlimits[ii+1]))
                        # Check that bins match expected
                        self.assertEqual(days, weather2[month, region, ii])

if __name__ == '__main__':
    unittest.main()

