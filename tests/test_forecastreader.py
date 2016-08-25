import unittest
from numpy import testing
from climate.forecastreader import *
from climate import forecasts

class TestForecastReader(unittest.TestCase):
    def test_zscore(self):
        weatherreader_z = MonthlyForecastReader(forecasts.temp_zscores_path, 'z-scores')
        z_weatherreader = MonthlyZScoreForecastReader(forecasts.temp_path, forecasts.temp_climate_path, 'temp')

        wz_iterator = weatherreader_z.read_iterator()
        wz_iterator = z_weatherreader.read_iterator()

        for month1, weather1 in w_iterator:
            month2, weather2 = wz_iterator.next()

            self.assertEqual(month1, month2)
            np.assert_allclose(weather1, weather2)
            print weather1[1000], weather2[1000]

if __name__ == '__main__':
    unittest.main()
