# Climate File Handling

This code defines the interface for reading from weather data files.

## Basic Interface

Each collection of weather data is represented as a class, which must
be a subclass of WeatherReader.  The WeatherReader class defines three
methods, which need to be written for each subclass:

 - `get_times`: Returns a list of the time values available in the
   entire collection.  The unit of time can vary from one dataset to
   another, but should describe the highest resolution at which data
   is available.  The values returned by `get_times` should correspond
   to the values returned by `read_iterator`, below.

 - `get_regions`: Returns a list all regions for which there is
   weather.

 - `get_dimension`: Returns a list of the weather variables defined in
   the file.  The length of this list defines the dimension `K`, used
   in `read_iterator`, below.

 - `read_iterator`: Yields `xarray` Datasets, in whatever chunks are
   convenient for reading the data.  The `time` coordinate should
   contain values from the list returned by `get_times`, and the
   `region` coordinate should contain all the values from
   `get_regions`.  All variables should have dimensions of `time` x
   `regions`.
   
Furthermore, if the class will support random acess, it should
implement `read_year`, which returns the `xarray` dataset for a given
year.

The `__init__` method of all subclasses must also call
`super(CLASSNAME, self).__init__(version, units)` to report the
version and units for the data.

## Files included

 - `reader.py`: Defines the top-level interface of `WeatherReader` and
   a helper class for reading data split into yearly chunks.

 - `dailyreader.py`: defines two basic classes for daily weather data
   and binned weather data.

 - `forecastreader.py`: defines two basic classes for monthly
   forecasts, and on-the-fly forecast z-scores.

 - `netcdfs.py`: Helper functions for reading NetCDFs in the CIL
   format.

 - `forecasts.py`: Helper function for reading forecast NetCDFs.

## Testing it

To run a simple test, call `tests/test_weatherreader.py` as follows:
```
python -m tests.test_weatherreader
```

This will create a daily reader and a binned reader, with data
corresponding to the same month, and check that they correspond.

Or try `tests/test_forecastreader.py`:
```
python -m tests.test_forecastreader
```

## Adding a new dataset

To add a dataset that reads from a new set of files, create a new
class as follows:

```
class NEWReader(WeatherReader):
    """Describe the data here."""

    def __init__(self, ...):
        super(NEWReader, self).__init__(VERSION, UNITS)
        ...

    def get_times(self):
        ...

    def get_dimension(self):
    	...

    def read_iterator(self):
        ...
```

And fill in each function definition as described above.

To add a transformation of an existing dataset, create a new class as
follows:

```
class NEWTransformedReader(WeatherReader):
    """Describe the transformation here."""

    def __init__(self, source):
    	super(NEWTransformedReader, self).__init__(source.version, UNITS)
        self.source = source

    def get_times(self):
        return self.source.get_times() # change this if time modified (e.g., further binning)

    def get_dimension(self):
    	return ['VARIABLE NAME']

    def read_iterator(self):
        for times, weather in self.source.read_iterator():
            transformed = ...
	        yield times, transformed
```

Here, the main parts that need to be filled in are the units in the
`__init__` function, the variable name returned by `get_dimension`,
and the transformation in `read_iterator`.
