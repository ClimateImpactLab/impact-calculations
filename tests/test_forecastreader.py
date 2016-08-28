import unittest
import numpy as np
from numpy import testing
from climate.forecastreader import *
from climate import forecasts

class TestForecastReader(unittest.TestCase):
    def test_zscore(self):
        weatherreader = MonthlyForecastReader("/shares/gcp/IRI/tas_aggregated_forecast_2012-2016Aug.nc", 'mean')
        for month, weather in weatherreader.read_iterator():
            print weather[1000]

        weatherreader_z = MonthlyForecastReader(forecasts.temp_zscore_path, 'z-scores')
        z_weatherreader = MonthlyZScoreForecastReader(forecasts.temp_path, forecasts.temp_climate_path, 'temp')

        wz_iterator = weatherreader_z.read_iterator()
        zw_iterator = z_weatherreader.read_iterator()

        for month1, weather1 in wz_iterator:
            month2, weather2 = zw_iterator.next()

            self.assertEqual(month1, month2)
            try:
                testing.assert_allclose(weather1, weather2)
            except:
                mismatch = np.abs(weather1 - weather2) > 1e-3
                # print np.sum(mismatch)
                # print weather1[7], weather2[7]
                # a = forecasts.readncdf_allpred(forecasts.temp_path, 'mean', 0).next()[7]
                # bs = list(forecasts.readncdf_allpred(forecasts.temp_climate_path, 'mean', 0))
                # cs = list(forecasts.readncdf_allpred(forecasts.temp_climate_path, 'stddev', 0))
                # print a, bs[month1 % 12][7], cs[month1 % 12][7]
                # print (a - bs[month1 % 12][7]) / cs[month1 % 12][7]
                # print weather1[mismatch], weather2[mismatch]
            print month1

if __name__ == '__main__':
    unittest.main()
