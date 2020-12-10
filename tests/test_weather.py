import pytest
import numpy as np
import xarray as xr
import numpy.testing as npt
from generate import weather
from climate import discover
from impactlab_tools.utils import files
from openest.generate import fast_dataset


# Utility functions
def get_yearorder(temp2year, weatherbundle):
    """Return the sequence of years returned by weatherbundle, using the temperature mapping."""
    years = []
    for year, ds in weatherbundle.yearbundles():
        years.append(temp2year.get(np.mean(ds['tas'][0]), None))
        if year > 2050:
            break
    return years


class StubWeatherReader():
    """WeatherReader-like stub for test input purposes only"""
    def __init__(self):
        self.version = None
        self.units = None
        self.dependencies = None
        self._regions = ["a"]
        self._data = {1000: 0, 1001: 1, 1002: 2}
        self._dims = ["time", "region"]

    def get_years(self):
        return list(self._data.keys())

    def read_year(self, y):
        v = self._data[y]

        # This whole setup is a hack to get some test data to run through
        # fast_dataset structures without breaking. I'm so sorry.
        region_coord_da = xr.DataArray(
            np.array(self._regions), [np.array(self._regions)], ("region",),
        )
        out = fast_dataset.FastDataset(
            {"temp": xr.Variable(self._dims, np.ones((1, 1)) * v)},
            coords={
                "time": np.array([y]),
                "region": region_coord_da,
            },
        )
        return out

    def get_dimension(self):
        return self._dims

    def get_regions(self):
        return self._regions


@pytest.fixture
def weatherbundle_simple(monkeypatch):
    """Get a simple weather bundle for tas."""
    monkeypatch.setattr(files, 'server_config', {'shareddir': 'tests/testdata'})
    bundleiterator = weather.iterate_bundles(discover.standard_variable('tas', 'year'))
    scenario, model, weatherbundle = next(bundleiterator)
    return weatherbundle


# Provides data for all tests
@pytest.fixture
def temp2year(monkeypatch, weatherbundle_simple):
    """Return a mapping between observed temperatures and the year they are observed."""
    temp2year = {}
    for year, ds in weatherbundle_simple.yearbundles():
        temp2year[np.mean(ds['tas'][0])] = year
        if year > 2050:
            break
    return temp2year

# The tests

def test_repeated(temp2year, weatherbundle_simple):
    """Does a median weatherset zig-zag properly?"""
    historybundle = weather.HistoricalWeatherBundle.make_historical(
        weatherbundle_simple, None)
    years = get_yearorder(temp2year, historybundle)
    npt.assert_equal(years[0], 1981)
    npt.assert_equal(max(np.abs(np.diff(years))), 1)
    npt.assert_equal(min(np.abs(np.diff(years))), 1)
    npt.assert_equal(np.max(years), 2005)

def test_shuffled(temp2year, weatherbundle_simple):
    """Does a Monte Carlo weatherset resample properly?"""
    historybundle = weather.HistoricalWeatherBundle.make_historical(
        weatherbundle_simple, 1)
    years = get_yearorder(temp2year, historybundle)
    npt.assert_approx_equal(np.mean(np.abs(np.diff(years))), 8.485714285714286)
    npt.assert_array_less(years, 2006)


class TestRollingYearTransformer:
    """Basic tests for RollingYearTransformer
    """

    def test_get_years(self):
        """Test RollingYearTransformer.get_years() basic behavior
        """
        n_roll = 2
        transformer = weather.RollingYearTransformer(rolling_years=n_roll)

        input_years = [0, 1, 2]
        # NOTE: expected is based on existing code behavior
        output_expected = [0, 1]

        output_actual = transformer.get_years(input_years)
        assert output_actual == output_expected

    def test_push2(self):
        """Test RollingYearTransformer.push() basic behavior with 2 obs

        This might break because of changes in fragile open_estimate.fast_dataset.
        Cuidado.
        """
        transformer = weather.RollingYearTransformer(rolling_years=2)

        # Making some fake Datasets, one for each time coord.
        # This whole setup is a hack to get some test data to run through
        # fast_dataset structures without breaking. I'm so sorry.
        region_coord_da = xr.DataArray(np.array(["a"]), [np.array(["a"])], ("region",))
        d0 = fast_dataset.FastDataset(
            {"temp": xr.Variable(["time", "region"], np.ones((1, 1)) * 0)},
            coords={
                "time": np.array([1000]),
                "region": region_coord_da,
            },
        )
        d1 = fast_dataset.FastDataset(
            {"temp": xr.Variable(["time", "region"], np.ones((1, 1)))},
            coords={
                "time": np.array([1001]),
                "region": region_coord_da,
            },
        )

        # Okay, things get weird here.
        # This transformer generator thing needs to be "primed" by `push()`ing
        # initial values, but it's going to throw `StopIteration` while it's
        # being primed because we're not yielding.
        y = d0.time.values.item()
        try:
            next(transformer.push(y, d0))
        except StopIteration:
            pass
        # The last items yielded after priming are the ones we actually want to
        # test.
        year_out, dataset_out = next(transformer.push(d1.time.values.item(), d1))

        # Test transformer-yielded values after generator was "primed"...
        assert year_out == 1000
        # This may break if fastdatasets change or xarray is swapped in. Ug.
        npt.assert_allclose(
            dataset_out._variables["temp"]._data,
            np.array([[0.0], [1.0]])
        )

    def test_push3(self):
        """Test RollingYearTransformer.push() basic behavior with 3 obs

        This might break because of changes in fragile open_estimate.fast_dataset.
        Cuidado.
        """
        transformer = weather.RollingYearTransformer(rolling_years=2)

        # Making some fake Datasets, one for each time coord.
        # This whole setup is a hack to get some test data to run through
        # fast_dataset structures without breaking. I'm so sorry.
        region_coord_da = xr.DataArray(np.array(["a"]), [np.array(["a"])], ("region",))
        d0 = fast_dataset.FastDataset(
            {"temp": xr.Variable(["time", "region"], np.ones((1, 1)) * 0)},
            coords={
                "time": np.array([1000]),
                "region": region_coord_da,
            },
        )
        d1 = fast_dataset.FastDataset(
            {"temp": xr.Variable(["time", "region"], np.ones((1, 1)))},
            coords={
                "time": np.array([1001]),
                "region": region_coord_da,
            },
        )
        d2 = fast_dataset.FastDataset(
            {"temp": xr.Variable(["time", "region"], np.ones((1, 1)) * 2)},
            coords={
                "time": np.array([1002]),
                "region": region_coord_da,
            },
        )

        # Okay, things get weird here.
        # This transformer generator thing needs to be "primed" by `push()`ing
        # initial values, but it's going to throw `StopIteration` while it's
        # being primed because we're not yielding.
        for d in (d0, d1):
            y = d.time.values.item()
            try:
                next(transformer.push(y, d))
            except StopIteration:
                continue
        # The last items yielded after priming are the ones we actually want to
        # test.
        year_out, dataset_out = next(transformer.push(d2.time.values.item(), d2))

        # Test transformer-yielded values after generator was "primed"...
        assert year_out == 1001
        # This may break if fastdatasets change or xarray is swapped in. Ug.
        npt.assert_allclose(
            dataset_out._variables["temp"]._data,
            np.array([[1.0], [2.0]])
        )


class TestHistoricalWeatherBundle:
    """Unit tests for basic behavior of generate.weather.HistoricalWeatherBundle
    """

    @pytest.mark.parametrize(
        "seed,expected",
        [
            (123, np.array([1002, 1001, 1002, 1002])),
            (None, np.array([1000, 1001, 1002, 1001])),
        ],
        ids=("seeded", "unseeded")
    )
    def test_init_seeding(self, seed, expected):
        """Test that initializes and samples correctly when seeded or not
        """
        victim = weather.HistoricalWeatherBundle(
            pastreaders=[StubWeatherReader()],
            futureyear_end=1003,
            seed=seed,
            scenario="rcp45",
            model="CCSM4"
        )
        npt.assert_equal(
            victim.pastyears,
            expected,
        )

    @pytest.mark.parametrize("seed", [123, None], ids=("seeded", "unseeded"))
    def test_init_pastyearslen(self, weatherbundle_simple, seed):
        """Test that self.pastyears initializes with correct len
        """
        victim = weather.HistoricalWeatherBundle(
            pastreaders=[StubWeatherReader()],
            futureyear_end=1003,
            seed=seed,
            scenario="rcp45",
            model="CCSM4"
        )
        assert len(victim.pastyears) == 4

    @pytest.mark.parametrize("n_readers", [1, 2], ids=("1 pastreaders", "2 pastreaders"))
    def test_yearbundles_years(self, n_readers):
        """Test yearbundles() yields years correctly
        """
        hwb = weather.HistoricalWeatherBundle(
            pastreaders=[StubWeatherReader()] * n_readers,
            futureyear_end=1003,
            seed=None,
            scenario="rcp45",
            model="CCSM4"
        )
        victim = list(hwb.yearbundles())

        # Unpack data for testing
        out_years = [y for y, _ in victim]

        assert out_years == [1000, 1001, 1002, 1003]

    @pytest.mark.parametrize("n_readers", [1, 2], ids=("1 pastreaders", "2 pastreaders"))
    def test_yearbundles_ds(self, n_readers):
        """Test yearbundles() yields dataset values correctly
        """
        hwb = weather.HistoricalWeatherBundle(
            pastreaders=[StubWeatherReader()] * n_readers,
            futureyear_end=1003,
            seed=None,
            scenario="rcp45",
            model="CCSM4"
        )
        victim = list(hwb.yearbundles())

        # Retrieving data from fastdataset is hackish pain. Will likely
        # break soon.
        out_values = [v._variables["temp"]._data.item() for _, v in victim]

        assert out_values == [0, 1, 2, 1]

    @pytest.mark.parametrize(
        "seed,expected",
        [
            (123, np.array([1994, 1983, 1983, 1987, 1998, 2000, 1991, 2003, 1982, 1981])),
            (None, np.arange(1981, 1991)),
        ],
        ids=("seeded", "unseeded")
    )
    def test_init_make_historical(self, weatherbundle_simple, seed, expected):
        """Test that make_historical() initializes and samples when seeded or not
        """
        victim = weather.HistoricalWeatherBundle.make_historical(
            weatherbundle=weatherbundle_simple,
            seed=seed,
        )
        npt.assert_equal(
            victim.pastyears[:10],
            expected,
        )

    @pytest.mark.parametrize("seed", [123, None], ids=("seeded", "unseeded"))
    def test_init_make_historical_pastyearslen(self, weatherbundle_simple, seed):
        """Test self.pastyears inits with correct len with make_historical()
        """
        victim = weather.HistoricalWeatherBundle.make_historical(
            weatherbundle=weatherbundle_simple,
            seed=seed,
        )
        assert len(victim.pastyears) == 120


class TestHistoricalRollingYearTransformer:
    """
    Integration test for HistoricalWeatherBundle and RollingYearTransformer
    """
    @pytest.mark.parametrize(
        "seed,expected",
        [
            (123, np.array([1002, 1001, 1002, 1002, 1000])),
            (None, np.array([1000, 1001, 1002, 1001, 1000])),
        ],
        ids=("seeded", "unseeded")
    )
    def test_init_seeding(self, seed, expected):
        """
        Test that init with RollingYearTransformer samples historical correctly
        """
        victim = weather.HistoricalWeatherBundle(
            pastreaders=[StubWeatherReader()],
            futureyear_end=1004,
            seed=seed,
            scenario="rcp45",
            model="CCSM4",
            transformer=weather.RollingYearTransformer(rolling_years=2)
        )
        npt.assert_equal(
            victim.pastyears,
            expected,
        )

    @pytest.mark.parametrize("n_readers", [1, 2], ids=("1 pastreaders", "2 pastreaders"))
    def test_yearbundles_years(self, n_readers):
        """
        Test yearbundles() yields years correctly when rolling 2 years
        """
        hwb = weather.HistoricalWeatherBundle(
            pastreaders=[StubWeatherReader()] * n_readers,
            futureyear_end=1004,
            seed=123,
            scenario="rcp45",
            model="CCSM4",
            transformer=weather.RollingYearTransformer(rolling_years=2)
        )
        victim = list(hwb.yearbundles())

        # Unpack data for testing
        out_years = [y for y, _ in victim]

        assert out_years == [1000, 1001, 1002, 1003]

    @pytest.mark.parametrize("n_readers", [1, 2], ids=("1 pastreaders", "2 pastreaders"))
    def test_yearbundles_ds(self, n_readers):
        """
        Test yearbundles() yields dataset values correctly when rolling 2 yrs
        """
        hwb = weather.HistoricalWeatherBundle(
            pastreaders=[StubWeatherReader()] * n_readers,
            futureyear_end=1004,
            seed=123,
            scenario="rcp45",
            model="CCSM4",
            transformer=weather.RollingYearTransformer(rolling_years=2)
        )
        victim = list(hwb.yearbundles())

        # Retrieving data from fastdataset is hackish pain. Will likely
        # break soon.
        out_values = [v._variables["temp"]._data for _, v in victim]

        # assert out_values == [0, 1, 2, 1]
        npt.assert_allclose(
            np.array([[[2.0], [1.0]],
                      [[1.0], [2.0]],
                      [[2.0], [2.0]],
                      [[2.0], [0.0]]]),
            np.array(out_values),
        )


if __name__ == '__main__':
    mapping = temp2year()
    test_repeated(mapping)
    test_shuffled(mapping)
