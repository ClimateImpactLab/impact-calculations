import unittest
from numpy import testing
from climate.forecastreader import *
from climate import forecasts

class TestForecastReader(unittest.TestCase):
    def test_zscore(self):
        weatherreader = MonthlyForecastReader(forecasts.temp_path, 'temp')
        weatherreader_z = MonthlyZScoreForecastReader(forecasts.temp_path, forecasts.temp_climate_path, 'temp')

        w_iterator = weatherreader.read_iterator()
        wz_iterator = weatherreader_z.read_iterator()

        for month1, weather1 in w_iterator:
            month2, weather2 = wz_iterator.next()

            self.assertEqual(month1, month2)
            print weather1[1000], weather2[1000]

if __name__ == '__main__':
    unittest.main()
