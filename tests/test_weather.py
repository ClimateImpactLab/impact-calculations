import numpy as np
import numpy.testing as npt
from generate import weather
from climate import discover

def get_weatherbundle():
    """Get a simple weather bundle for tas."""
    bundleiterator = weather.iterate_bundles(discover.standard_variable('tas', 'year'))
    scenario, model, weatherbundle = bundleiterator.next()
    return weatherbundle

def get_temp2year():
    """Return a mapping between observed temperatures and the year they are observed."""
    temp2year = {}
    weatherbundle = get_weatherbundle()
    for year, ds in weatherbundle.yearbundles():
        temp2year[np.mean(ds['tas'][0])] = year
    return temp2year

def get_yearorder(temp2year, weatherbundle):
    """Return the sequence of years returned by weatherbundle, using the temperature mapping."""
    years = []
    for year, ds in weatherbundle.yearbundles():
        years.append(temp2year.get(np.mean(ds['tas'][0]), None))
    return years

def test_repeated(temp2year):
    """Does a median weatherset zig-zag properly?"""
    weatherbundle = get_weatherbundle()
    historybundle = weather.HistoricalWeatherBundle.make_historical(weatherbundle, None)
    years = get_yearorder(temp2year, historybundle)
    npt.assert_equal(years[0], 1981)
    npt.assert_equal(max(np.abs(np.diff(years))), 1)
    npt.assert_equal(min(np.abs(np.diff(years))), 1)
    npt.assert_equal(np.max(years), 2005)

def test_shuffled(temp2year):
    """Does a Monte Carlo weatherset resample properly?"""
    weatherbundle = get_weatherbundle()
    historybundle = weather.HistoricalWeatherBundle.make_historical(weatherbundle, 1)
    years = get_yearorder(temp2year, historybundle)
    npt.assert_approx_equal(np.mean(np.abs(np.diff(years))), 8.6470588235294)
    npt.assert_equal(np.max(years), 2005)

if __name__ == '__main__':
    temp2year = get_temp2year()
    test_repeated(temp2year)
    test_shuffled(temp2year)


