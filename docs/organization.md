This file describes the organization of the code.

## Basic concepts/classes:

* A `Curve` class (see `open-estimate`) represents a portion of the dose-response curve. It may be a subset of the terms of an OLS model, or a segement representing the response to a segment of temperatures. Typically, these are represented as `SmartCurve` classes.
* A `CurveGenerator` class (see `open-estimate` and `adaptation/curvegen*.py`) produces a curve for a given region and year. `CurveGenerator`s encapsulate the adaptation logic, producing static curves.
* A `Calculation` class (see `open-estimate`) represents a stream-processor, which takes weather data as an input and produces (typically) a single result as an output.
* An `Application` class (see `open-estimate`) handles the actual calculations for a given region. `Application` objects are like `Calculation` instances, and exist for each region.

## Weather data

Weather data is specific to an RCP and a GCM. We want to abstract from the specifics of the source and structure of that data.

The weather handling system consists of `WeatherReader` classes (`climate/reader.py`). These iteratively produce `xarray` objects for a particular kind of weather in a particular year.
See https://gitlab.com/ClimateImpactLab/Impacts/impact-calculations/blob/master/climate/README.md for details.

Weather is referred to by a string in configuration files, which may include additional calculations. This system is implemented in `climate/discover.py`. See `Climate naming` in https://gitlab.com/ClimateImpactLab/Impacts/impact-calculations/blob/master/docs/imperics.md for details.

Multiple `WeatherReader` objects are then wrapped into a single `WeatherBundle` object (`generate/weather.py`) for processing through the calculation system. This class provides some additional functionality, such as multi-year transformation, the stitching together of historical and future projections, and the creation of historical projected climate data.

## Socioeconomic data

Socioeconomic data is specific to an SSP and an IAM.

*See also the Building the baseline data.docx document.*
