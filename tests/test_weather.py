import pytest
import numpy as np
import numpy.testing as npt
from generate import weather
from climate import discover
from impactlab_tools.utils import files

## Test that weather bundles are working properly.

# Utility functions

def get_weatherbundle():
    """Get a simple weather bundle for tas."""
    bundleiterator = weather.iterate_bundles(discover.standard_variable('tas', 'year'))
    scenario, model, weatherbundle = next(bundleiterator)
    return weatherbundle

def get_yearorder(temp2year, weatherbundle):
    """Return the sequence of years returned by weatherbundle, using the temperature mapping."""
    years = []
    for year, ds in weatherbundle.yearbundles():
        years.append(temp2year.get(np.mean(ds['tas'][0]), None))
        if year > 2050:
            break
    return years

# Provides data for all tests
@pytest.fixture
def temp2year(monkeypatch):
    """Return a mapping between observed temperatures and the year they are observed."""
    monkeypatch.setattr(files.server_config, 'shareddir', 'tests/testdata')

    temp2year = {}
    weatherbundle = get_weatherbundle()
    for year, ds in weatherbundle.yearbundles():
        temp2year[np.mean(ds['tas'][0])] = year
        if year > 2050:
            break
    return temp2year

# The tests

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
    npt.assert_approx_equal(np.mean(np.abs(np.diff(years))), 8.485714285714286)
    npt.assert_array_less(years, 2006)

if __name__ == '__main__':
    mapping = temp2year()
    test_repeated(mapping)
    test_shuffled(mapping)
