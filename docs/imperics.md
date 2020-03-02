Under Imperics, impact calculations can be specified by `.yml` files
under the `impacts/<sector>/` directories.  The general organization
of these files is as follows:

1. Universe and climate identification
2. Models list (`models:`)
   1. Basic model configration
   2. Either a single specification configuration (`specification:`)
      containing a post-specification calculation (`calculation:`), or
      multiple named specifications (`specifications:`), followed a
      full calculation (`calculation:`).

Some teriminology:

A "model" is a set of calculations performed to apply a CSVV to future
weather data.  A model is deamed to consist of a set of configurable
"calculation" steps, each of which generally produces an intermediate
result to be saved to the final result file.  A special kind of
calculation translates high-resolution weather data to yearly values,
and these calculations rely on a "specification", which describes how
the dose-response curve varies across space and time.

Configuration file structure paradigms:

The configuration file consists of a tree of sub-configurations.  At
each level of the tree, the branches may either be simply listed, if
only the order matters, like:

```
 - first branch
 - second branch
 - third branch
```

or named, if the order does not matter, like:
```
first: branch
second: branch
third: branch
```

or both, if both the name and the order matters, like:
```
 - first: branch
 - second: branch
 - third: branch
```

Lower branches of the tree inherit the named contents of their upper
branches, so you can think of the higher-level configuration applying
to all lower levels.

## Universe and climate identification

The top-level configuration specifies the universe of climate and
economic models to iterate through in generating results.  Internally,
this creates a climate discoverer, which captures all of
high-resolution weather to be used in any model.

This section can interpret the following named parameters:

* `timerate` (required): The rate of all the high-resolution weather
  data.  May be `day`, `month`, or `year`.  If not all of the weather
  uses the same time rate, it needs to be translated so it does.
* `climate` (required): A list of the weather data to be used, to be
  interpreted by `climate.discover::standard_variable`.
* `rolling-years` (optional): Number of years to be included in each
  result year's calculation, as a rolling sequence.
* `models` (required): The list of model configurations.

Basic model configration:

* `csvvs` (required): A filepath for a CSVV file or path expansion for a
  collection of CSVVs that will be processed through the model.
  Filepath expansions are interpretted by
  https://docs.python.org/2/library/glob.html

* `clipping` (required): Should curve values less the region minimum be replaced with the region minimum?  Currently this only supports clipping of curves that are expected to have a minimum.  The default limits for the region-specific temperature at which this can occur are 10C and 25C, but these can be adjusted with `clip-mintemp` and `clip-maxtemp` options.

* `covariates` (required): A list of known covariate names,
  interpretted by `interpret.specification::get_covariator`.  See the
  Covariates Expressions below, for more information.
  
* `description` (required): A description for the final result of the
  calculation.
  
* `csvv-organization` (optional):
  Typically blank, but may be included if the CSVV file has the
  following known organizational scheme:
  - `three-ages`: The parameters are grouped in thirds, with the first
    third for young people (and intended for files with a `-young`
    suffix); the second third for older (suffix `-older`), and the
    third third for oldest (suffix `-oldest`).
  - `lowhigh`: The parameters are divided into two groups, with the first
    half for low-risk labor (and intended for files with a `-lowrisk`
    suffix); the second half for high-risk labor (suffix `-highrisk`).

* `within-season` (optional): All weather-driven covariates and
  weather parameters will be limited to seasons specified by the given
  CSV file.  The columns of file should include `hierid`,
  `plant_date`, `harvest_date`, `plant_month`, `harvest_month`.

## Climate naming

The `climate.discover::standard_variable` allows a number of
modifications to standard variable names.

 - A path
 - A variable followed by `==<version>`
 - `<name> = ` followed by another standard variable definition
 - `<name>.<transform>`: A known transformation of a variable. The transformation is by default done at the daily level before being transformed to the desired time rate; the name could have the suffix `-` to be also looked up at the daily level.
 - `<name> * <name>`: A product of two variables, taken at the daily level before any aggregation.

Some of the known transformations are:
 - `histclim`: The historical climate only.
 - `gddkdd(low, high)`: generate GDD and KDD values with the given temperature limits
 - `step(limit, before, after)`: Generate a step function, stepping from `before` to `after` at the value `limit`.
 - `country`: country level averages

## Specification configuration:

The specification configuration can be specified by the following two
structures:
```
specification:
   <configuration>
   calculation:
    - <post-specification steps>
	- ...
```

or, if there are multiple weather-to-year curves:
```
specifications:
	<name>:
		<configuration>
	...
calculation:
	- <calculation>
```

The specification configuration options are described below:

* `description` (required): The description for the dose-response
  curve.
* `depenunit` (required): The units of the dependent units.
* `functionalform` (required): The functional form of the
  coefficients.  It may be one of `polynomial`, `cubicspline`, or
  `coefficients`.
* `beta-limits` (optional): Specifies minimum and maximum values for
  each beta (post-covariated) coefficient, as in:
  ```
  beta-limits:
      kdd-30: -inf, 0
  ```
  
The independent variables are specified differently according to the
functional form.

For polynomial form has the following additional configuation options:

* `variable` (required): The name of the weather variable, or prefix
  for higher powers.
* `coeffvar` (optional): The name of the CSVV predname, or prefix for
  higher powers.  Defaults to `variable`.
* `indepunit` (required): The unit for the independent variable.
* `allow-raising` (optional): If `yes`, the higher powers of the
  variable will be calculated from the linear form, if the other
  options are not available.

The cubic spline form has the following additional options:

* `prefix` (required): The prefix for cubic spline variables.
* `knots` (required): The weather values for the knots of the cubic spline.
* `indepunit` (required): The unit for the independent variable.

The coefficients form has the following additional options:

* `variables` (required): A named list of variables, each definition
  may be a mini-calculation or a known variable, but must be of the
  form:
  `<variable-name>: <variable definition> [<unit>]`

## Covariates Expressions:

Here is the current list of known covariates, most of which are
long-run averages (typically with a Bartlett kernel):

* `loggdppc`: Log GDP per capita
* `logpopop`: Log population-weighted population density
* `incbin`: Binned income (indicators for each log income bin); takes a list of N+1 log income knots.
* `climtas`: Average temperature (C)
* `ir-share`: Share of the area under irrigation

Modifications of covariates:

* `clim...`: Yearly average of a weather variable specified in the
  `climate` list.
* `seasonal...`: The seasonal prefix only is like the `clim...` prefix
  except that it the weather variable values for the `within-season` span.
* `*`: Multiplication of two covariates.
* `^`: A covariate raised to a power.

Additionally, `hierid-...` can be given as a covariate to add a constant for 
just a subset of the impact regions. To define the regions that will have a 
non-zero value for this term, this covariate takes a list of one or more impact 
region hierarchical "region-keys", as defined in /shares/gcp/regions/hierarchy.csv. 
The covariate name should match a variable/"covarnames" value in the projection 
run's CSVV file. If an impact-region falls within one of the covariates' regions, 
that CSVV value is used for the covariate term. Otherwise the term is 0.0. 
The `...` in the covariate name can be any arbitrary name.


## Calculation (or post-calculation) options:

The list of calculation step known can be given by
`interpret.available`.  Each calculation step has different
arguments.  They can be divided into two collections:

Weather-to-result calculations:

These calculations take a dose-response curve generator, which is
applied to high resolution weather, and gives out yearly values.

Here are the most common ones:

* `YearlySumDay`: Sum the result of the curve at the daily level.
* `YearlySumIrregular`: Sum whatever set of weather is given, applied
  to the curve.

Yearly-to-yearly calculations:

These take previous results given at a yearly level and produce new
results at a yearly level.

Here are some of the standard ones:

* `Sum`: Sum a list of other previous calculations.
* `Rebase`: Subtract off the average previous result from 2001 - 2010.
* `Expoonentiate`: Report the exponentiate of the previous result.

### Specifying a model

Typically, each calculation takes as its input the previous
calculation's output.  In some cases (for certain weather-to-result
calculations), there need to be several models or specifications
defined.  This is done by maknig a `specifications` list within a
model block, naming each specification.  Then those same names are
used in the calculation, by using the `model:` property.

The model property can take the following forms of objects:

 - A name from the `specifications` list
 
 - The `step()` function which takes three arguments: a variable name,
   a step limit, and a before and after step function value.  Like
   `step('tas', 20, [0, 1])`.

 - A product of two of the above, using `A * B`.
 
