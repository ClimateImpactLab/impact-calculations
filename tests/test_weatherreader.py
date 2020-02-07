import unittest
import numpy as np
from numpy import testing
from climate.dailyreader import *

class TestWeatherReader(unittest.TestCase):
    def test_bincompare(self):
        # Check the first month of daily values
        print "Reading from the daily data files."
        template1 = "tests/testdata/tas_day_aggregated_historical_r1i1p1_CCSM4_%d.nc"
        weatherreader1 = DailyWeatherReader(template1, 1981, 'SHAPENUM', 'tas')

        print weatherreader1.version, weatherreader1.units
        self.assertEqual(weatherreader1.units, "Celsius")

        self.assertEqual(len(weatherreader1.get_dimension()), 1)

        alltimes1 = weatherreader1.get_times()

        # Compare it to the first month of binned values
        print "Reading from the binned data files."
        template2 = "tests/testdata/tas_Bindays_aggregated_historical_r1i1p1_CCSM4_%d.nc"
        weatherreader2 = YearlyBinnedWeatherReader(template2, 1981, 'SHAPENUM', 'DayNumber', bindim='bins', binvariable='bin_edges')

        print weatherreader2.version, weatherreader2.units
        self.assertEqual(weatherreader2.units, "days")

        self.assertEqual(len(weatherreader2.get_dimension()), 12)

        alltimes2 = weatherreader2.get_times()

        iterator1 = weatherreader1.read_iterator()
        iterator2 = weatherreader2.read_iterator()
        while alltimes1 or alltimes2:
            ds1 = iterator1.next()
            ds2 = iterator2.next()

            yyyyddd1 = ds1.time.dt.year * 1000 + ds1.time.dt.dayofyear
            testing.assert_array_equal(alltimes1[:len(ds1.time)], yyyyddd1)
            alltimes1 = alltimes1[len(ds1.time):]

            testing.assert_array_equal(alltimes2[0], ds2.attrs['year'])
            alltimes2 = alltimes2[1:]

            binlimits = [-np.inf, -17, -12, -7, -2, 3, 8, 13, 18, 23, 28, 33, np.inf]
            bincenters = [-19.5] + list((np.array(binlimits[1:-2]) + np.array(binlimits[2:-1])) / 2) + [35.5]

            var1 = ds1.tas
            var2 = ds2.DayNumber
            self.assertEqual(var1.shape[1], var2.shape[0])

            for region in range(20): # iterate through regions
                regtas = var1[:, region]
                    
                dailymean = np.mean(regtas[(regtas > -17) & (regtas < 33)])
                binnedmean = np.sum(var2[region, 1:-1] * bincenters[1:-1]) / sum(var2[region, 1:-1])
                testing.assert_almost_equal(dailymean, binnedmean, decimal=0)
                    
                aggthenbin = []
                    
                for ii in range(len(binlimits)-1):
                    days = np.sum((regtas >= binlimits[ii]) & (regtas < binlimits[ii+1]))
                    aggthenbin.append(days)

                    # Check that bins match expected
                    var2days = float(var2[region, ii] / (24*3600) / 1e9)
                    testing.assert_almost_equal(float(days), var2days, decimal=-1)
            break # stop after 1981 for now

if __name__ == '__main__':
    unittest.main()

