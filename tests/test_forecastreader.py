import unittest
import numpy as np
from numpy import testing
from climate.forecastreader import *
from climate import forecasts

class TestForecastReader(unittest.TestCase):
    def test_zscore(self):
        weatherreader = MonthlyForecastReader("/shares/gcp/climate/IRI/tas_aggregated_forecast_2012-2016Aug.nc", 'mean')
        for ds in weatherreader.read_iterator():
            self.assertAlmostEqual(ds['mean'][1001], 24.36522102355957)
            break

        weatherreader_z = MonthlyForecastReader("/shares/gcp/climate/IRI/tas_zscores_aggregated_forecast_2012-2016Aug.nc", 'z-scores')
        z_weatherreader = MonthlyZScoreForecastReader(weatherreader,
                                                      "/shares/gcp/climate/IRI/tas_aggregated_climatology_1981-2010-new.nc", 'mean',
                                                      "/shares/gcp/climate/IRI/tas_aggregated_climatology_1981-2010-new.nc", 'stddev', '3d')

        wz_iterator = weatherreader_z.read_iterator()
        zw_iterator = z_weatherreader.read_iterator()

        for ds1 in wz_iterator:
            ds2 = zw_iterator.next()
            self.assertAlmostEqual(ds1['z-scores'][3], ds2['mean'][3])
            return

if __name__ == '__main__':
    unittest.main()
