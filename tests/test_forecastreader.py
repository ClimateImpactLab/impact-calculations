import unittest
from numpy import testing
from climate.forecastreader import *
from climate import forecasts

class TestForecastReader(unittest.TestCase):
    def test_zscore(self):
        weatherreader_z = MonthlyForecastReader(forecasts.temp_zscore_path, 'temp')
        z_weatherreader = MonthlyForecastReader(forecasts.temp_path, forecasts.temp_climate_path, 'temp')

        wz_iterator = weatherreader_z.read_iterator()
        zw_iterator = z_weatherreader.read_iterator()

        for month1, weather1 in wz_iterator:
            month2, weather2 = zw_iterator.next()

            self.assertEqual(month1, month2)
            testing.assert_allclose(weather1, weather2)

if __name__ == '__main__':
    unittest.main()
