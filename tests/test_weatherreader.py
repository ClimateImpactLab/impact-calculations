import unittest
import numpy as np
from numpy import testing
from climate.dailyreader import *

class TestWeatherReader(unittest.TestCase):
    def test_bincompare(self):
        # Check the first month of daily values
        print "Reading from the daily weather data files."
        template1 = "/shares/gcp/BCSD/grid2reg/cmip5/historical/CCSM4/tas/tas_day_aggregated_historical_r1i1p1_CCSM4_%d.nc"
        weatherreader1 = DailyWeatherReader(template1, 1981, 'tas')

        print weatherreader1.version, weatherreader1.units
        self.assertEqual(weatherreader1.units, "Celsius")

        self.assertEqual(len(weatherreader1.get_dimension()), 1)

        times_january = weatherreader1.get_times()[:31]
        for times, weather in weatherreader1.read_iterator():
            testing.assert_array_equal(times_january, times[:31])
            daily_january = weather[:31, 1001]
            break

        # Compare it to the first month of binned values
        print "Reading from the binned data files."
        template2 = "/shares/gcp/BCSD/grid2reg/cmip5_bins/historical/CCSM4/tas/tas_Bindays_aggregated_historical_r1i1p1_CCSM4_%d.nc"
        weatherreader2 = BinnedWeatherReader(template2, 1981, 'DayNumber')

        print weatherreader2.version, weatherreader2.units
        self.assertEqual(weatherreader2.units, "days")

        self.assertEqual(len(weatherreader2.get_dimension()), 12)

        times_janfeb = weatherreader2.get_times()[:2]
        for times, weather in weatherreader2.read_iterator():
            testing.assert_array_equal(times_janfeb, times[:2])
            binned_january = weather[0, 1001]
            print binned_january
            print daily_january

            # Check that bins match expected
            binlimits = [-np.inf, -17, -12, -7, -2, 3, 8, 13, 18, 23, 28, 33, np.inf]
            for ii in range(0, len(binlimits)-1):
                days = np.sum((daily_january >= binlimits[ii]) & (daily_january < binlimits[ii+1]))
                print binlimits[ii], binlimits[ii+1], days
                self.assertEqual(days, binned_january[ii])
            break

if __name__ == '__main__':
    unittest.main()

