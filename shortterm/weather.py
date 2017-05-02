import numpy as np
from netCDF4 import Dataset
from scipy.stats import norm
from generate.weather import WeatherBundle, ReaderWeatherBundle
from climate import forecasts, forecastreader
from openest.generate.weatherslice import TriMonthlyWeatherSlice

class ForecastBundle(ReaderWeatherBundle):
    def __init__(self, reader, hierarchy='hierarchy.csv'):
        super(ForecastBundle, self).__init__(reader, 'forecast', 'IRI', hierarchy=hierarchy)

    def get_months(self):
        return self.reader.get_times(), self.reader.time_units

    def monthbundles(self, maxyear=np.inf):
        for weatherslice in self.reader.read_iterator():
            yield weatherslice

class CombinedBundle(WeatherBundle):
    def __init__(self, bundles, hierarchy='hierarchy.csv'):
        super(CombinedBundle, self).__init__('forecast', 'IRI', hierarchy)
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
                weatherslice = iterator.next()
                assert month == weatherslice.times[0]
                if len(weatherslice.weathers.shape) < 3:
                    weatherslice.weathers = np.expand_dims(weatherslice.weathers, axis=2)
                results.append(weatherslice.weathers)

            yield TriMonthlyWeatherSlice([month], np.concatenate(results, axis=2))

if __name__ == '__main__':
    print np.mean(forecasts.readncdf_lastpred(forecasts.temp_path, "mean", 0))
    print np.mean(forecasts.readncdf_lastpred(forecasts.prcp_path, "mean", 0))

    bundle = ForecastBundle(forecastreader.MonthlyStochasticForecastReader(forecasts.temp_path, 'temp', 0, .5))
    print np.mean(bundle.monthbundles().next()[1])

    for monthvals in forecasts.readncdf_allpred(forecasts.temp_path, 'mean', 0):
        print monthvals[1000]
