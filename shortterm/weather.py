import numpy as np
from netCDF4 import Dataset
from scipy.stats import norm
from impacts.weather import WeatherBundle, ReaderWeatherBundle
from climate import forecasts, forecastreader

class ForecastBundle(ReaderWeatherBundle):
    def get_months(self):
        return self.reader.get_times(), self.reader.time_units

    def monthbundles(self, maxyear=np.inf):
        for month, values in self.reader.read_iterator():
            yield month, values

class CombinedBundle(WeatherBundle):
    def __init__(self, bundles, hierarchy='hierarchy.csv'):
        super(CombinedBundle, self).__init__(hierarchy)
        self.bundles = bundles
        self.dependencies = set()
        for bundle in bundles:
            self.dependencies.update(bundle.dependencies)
        self.dependencies = list(self.dependencies)

        self.load_regions()
        self.version = bundles[0].version
        self.units = [bundle.units for bundle in bundles]

    def get_months(self):
        return self.bundles[0].get_months()

    def monthbundles(self, qval, maxyear=np.inf):
        months, months_title = self.get_months()
        iterators = [bundle.monthbundles(qval) for bundle in self.bundles]
        for month in months:
            results = []
            for iterator in iterators:
                monthii, result = iterator.next()
                assert month == monthii
                results.append(result)

            yield month, np.array(results)

if __name__ == '__main__':
    print np.mean(forecasts.readncdf_lastpred(forecasts.temp_path, "mean", 0))
    print np.mean(forecasts.readncdf_lastpred(forecasts.prcp_path, "mean", 0))

    bundle = ForecastBundle(forecastreader.MonthlyStochasticForecastReader(forecasts.temp_path, 'temp', 0, .5))
    print np.mean(bundle.monthbundles().next()[1])

    for monthvals in forecasts.readncdf_allpred(forecasts.temp_path, 'mean', 0):
        print monthvals[1000]
