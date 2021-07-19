The aggregator tool is a post-processing tool which operates on
impact-region (IR) level generated response files.  Any impact-region
files can be aggregated. To do so, you need to describe the
aggregation weighting scheme, which is encoded in a yaml configuration
file, described below.

It generates three kinds of files:

 - `-levels` files, which are scaled versions of the output files,
   using time-varying scaling, at the IR-level.
 - `-aggregated` files, which aggregate IR regions up to higher
   ADM-level, country-level, regional international groupings, and
   globally aggregated outputs.
 - `-costs` files, which estimate the cost bounds for adaptation. For
   cost files to be generated, an adaptation costs script needs to be
   provided (talk with James for details).

If the raw outputs are *y_it*, then the scaling scheme in the levels
files produces *w_it y_it*, and the aggregation system computes
*(sum_i w_it y_it) / sum_i w_it* or *sum_i w_it y_it* (depending on
the denominator specification).

Aggregation is initiated by calling,
```$ ./aggregate.sh configs/<CONFIG-FILE>.yml [N]```
where `<CONFIG-FILE>.yml` is a configuration file including the
options below, and `[N]` is an optional argument to initate N
processes.  If `[N]` is missing, a single process is started and the
results are printed directly to the terminal; otherwise, the processes
are started in the background.

A single aggregation process will search through all output
directories for complete files, and generate the corresponding
`-levels`, `-aggregated`, and `-costs`.

The following options are available for a configuration file for the
aggregation process:

Required:

 - `outputdir`: The root directory for searching for files.  This
   should be a version-specific folder, within a sector-specific
   folder.
 - `weighting`: A single weighting scheme used for both scaling and
   aggregation (see Weighting Schemes below).  Alternatively, the
   scaling and aggregation can use different weighting schemes using
   the configuration parameters `levels-weighting` and
   `aggregate-weighting`.  Alternatively-alternatively, the
   aggregation weighting can use different multiplicative factors in
   its numerator and denominator, with `aggregate-weighting-numerator`
   and `aggregate-weighting-denominator`.  A special value for
   `aggregate-weighting-denominator` is `sum-to-1`, which causes no
   demoninator to be used in the aggregation calculation.
   
Optional:

 - `infix`: A label inserted before the term `-levels` and
   `-aggregated`, to distinguish multiple weighting schemes.
 - `timeout`: The number of hours to allow the process to work, before
   considering a directory abandoned (default: 24).
 - `check-variable`: The aggregation code attempts to validate output
   files before attempting to aggregate them. The checks are defined
   in `generate.checks.check_result_100years`. These checks currently
   include checking the size of the result-- at least 100 years, where
   the standard length is 120, and the number of regions, defaulted to
   24378 but overrideable with the `region-count` configuration
   option-- and that an arbitrary year of values all look valid.
 - `costs-config` a dictionary containing all the necessary information to compute adaptation costs. See [the Adaptation Costs files](#Adaptation-Costs-files) section for details. 

Filtering Targets (also Optional):

 - `rcp`: Only aggregate results from the given RCP.
 - `gcm`: Only aggregate results from the given GCM.
 - `ssp`: Only aggregate results from the given SSP (e.g., `SSP3`).
 - `iam`: Only aggregate results from the given IAM (high or low).
 - `batch`: Only aggregate results from the given batch (e.g., `median` or `batch3`).
 - `mode`: Only aggregate results produced by the given mode.  Options: `median`, `montecarlo`, or `xsingle` (median and montecarlo, but not diagnostic).
 - `targetdir`: Only aggregate results in the given leaf output
   directory.  This should be a full path name (e.g.,
   `/shares/gcp/.../SSP3`)  Do not include a tailing slash.
 - `basename`: Only aggregate results for a given basename (the
   portion of the filename before `.nc4`, typically copied from the
   name of the CSVV file).
 - `only-farmers`: Takes a list of farmer suffixes to aggregate and only
   aggregates these. The list entries should be drawn from '',
   'incadapt', 'noadapt', 'histclim', 'incadapt-histclim',
   'noadapt-histclim'.
 - `only-variables`: Takes a list of variables contained in the file
   to process. If missing, all variables will be processed.

## Adaptation Costs files

The adaptation cost files and their aggregated version can be generated along the aggregation of impact files. For this, the user must pass a dictionary `costs-config` entry in the config. Two examples are provided at the end of this section. 

Required keys are : 

 - `command-prefix` a string representing the command to run the cost script set up by the user in the command line.
 - `ordered-args` containing arguments to be passed to the costs script. It shoud be represented by a dictionary. It should contain at least one of the below keys : 

   - `known-args` list of strings representing arguments that are known to the code and that depend on data known to the system during runtime (e.g. target directory). Currently available : `['clim_scenario', 'clim_model', 'impactspath', 'batchwd','econ_scenario','iam','seed-csvv', 'costs-suffix']`
   - `extra-args` list of strings, representing extra arguments to be passed to the cost script.  

 - `check-variable-costs` a string. It is required to perform checks that are analogous to those performed with `check-variable` (see above), but for costs files.

Optional keys are : 

- `costs-suffix` : a string. The default value is '-costs'. It is used to determine the name of the aggregated cost files. If `costs-suffix` starts with `-` it is interpreted as a suffix and the system will name the aggregated cost files after the prefix of the targetdir response files, and will look for those names in preliminary checks. If it doesn't start with `-`, the aggregated cost files will have as a full name the value of `costs_suffix`. The system also uses the value of `costs-suffix` for the known argument `costs-suffix` in `known-args`, if the user requires this known argument.
- `infix` : A label inserted before `costs-suffix` historically available to distinguish multiple weighting schemes.
- `meta-info`: a dictionary of strings to fill in the aggregated adaptation costs netcdf files meta information. Required keys : 
   - `description`
   - `version`
   - `author`


Example 1 : 


```
costs-config: 
  command-prefix: 'Rscript /home/etenezakis/CIL_repo/agriculture/1_code/3_projections/4_run_projections/adaptation_costs/tmp_and_prcp_costs.R'
  ordered-args:
    extra-args:
      - rice
      - 13
      - unused
    known-args:
      - batchwd
      - clim_model
      - clim_scenario
      - econ_scenario
      - iam
  costs-suffix: adaptation_costs
  check-variable-costs: adpt.cost.cuml
  meta-info: 
    description: "costs of yield adaptation to temperature and precipitation long term changes"
    version: "YIELDS-2021-06-03"
    dependencies: "tmp_and_prcp_costs.R"
    author: "Andy Hultgren"
```

Example 2 : 


```
costs-config: 
  command-prefix: 'Rscript /home/etenezakis/CIL_repo/impact-calculations/generate/cost_curves.R'
  ordered-args:
    known-args:
      - clim_scenario
      - clim_model
      - impactspath
      - costs-suffix
      - iam
  costs-suffix: -costs
  check-variable-costs: costs_lb
  meta-info:
    description: 'Upper and lower bounds costs of adaptation calculation.'
    version: 'DEADLY-2016-04-22'
    dependencies: 'TEMPERATURES, ADAPTATION-ALL-AGES'
    author: 'Tamma Carleton'
```


## Weighting Schemes

A weighting schemes consists of an expression that can consist of a
known time-varying scaling term, a constant, or products or quotients
of scaling terms and constants.

Possible components:

 - Constant (e.g., 10).
 - `area`: Weight aggregation by land area.
 - `population`: Total population in each region.
 - `age0-4`, `age5-64`, or `age65+`: Age-specific population in each
   region.
 - `agecohorts`: Interpret the result name to find the appropriate
   age-specific population to use.  Use `age0-4` for `*-young`,
   `age5-64` for `*-older` and `age65+` for `*-oldest`.
 - `income`: Income per capita, in PPP USD, as defined by the SSPs.
 - Term ` * ` Term: The product of two terms (can be chained).  There must be spaces the the left and right of the symbol.
 - Term ` / ` Term: The quotient of two terms (can be chained).  There must be spaces the the left and right of the symbol.  Terms
   are computed sequentially, so *(a b) / (c d)* should be described
   as `a * b / c / d`.
 - `constcsv/<PATH>:<HIERID>:<VALUE>`: Read the weights from a CSV or DTA
   file, applying constant weights to each region.  `<PATH>` is a
   relative path from the server shared directory.  `<HIERID>` is the
   name of the column specifying the names of the impact regions.
   `<VALUE>` is either a column name, or `sum(<COLUMN>)`, where the
   latter may be used if more than one row applies to the same impact
   region.
 - `<PATH>:<HIERID>:<YEAR>:>VALUE>`: As with `constcsv` above, but
   allowing time-varying weights with the inclusion of a column
   specifying the year, in `<YEAR>`.  Years prior to the initial year
   in the file or after the final year will be given the first or last
   year's value, respectively.  If the file does not contain a hierid
   for the impact region, it will try to use the one from the
   country's ADM3 code, and otherwise the mean.

The `datastore.weights` script also allows these weighting schemes to
be output in CSV format for each region and year.  To do this, run
```
python -m datastore.weights <WEIGHTING> <IAM> <SSP> > <OUTPUT-FILE>
```
where `<WEIGHTING>` is a weighting configuration description as above
(excluding the `agecohorts` specification, which requires a file to be
fully specified) and should be in quotes if it contains spaces;
`<IAM>` is `low` or `high`; `<SSP>` is `SSP#` where # is a number
between 1 and 5, inclusive; and `<OUTPUT-FILE>` is a filename (ending
with `.csv`) where the result should be stored.  Note the single `>`
symbol above is required for the results to be written to this file.

## Examples:

Aggregate results by population, as -aggregated files. This will also produce -levels files
that are the total impact across all people (the impacts times the
population), which is sensible if the impact is a per-person result.

```
outputdir: [...]
weighting: population
```

As above, but aggregate results by total GDP, and report total dollars
lost for a per-person impact.

```
outputdir: [...]
# Levels are minutes * wage / elasticity; wage = income / (250 days * 6 hours * 60 minutes); elasticity = 0.5
levels-weighting: population * income / 180000
aggregate-weighting: population * income
infix: wage
```

Create kevels files by multiplying each result by the corresponding
energy price, and the aggregated files by taking these price-scaled
results and aggregating them by population. The resulting files will
be called *-withprice-levels.nc4 and *-withprice-aggregated.nc4 to
distinguish them from other aggregations.

```
outputdir: [...]
levels-weighting: social/baselines/energy/IEA_Price_FIN_Clean_gr014_GLOBAL_COMPILE.dta:country:year:other_energycompile_price
aggregate-weighting-numerator: population * social/baselines/energy/IEA_Price_FIN_Clean_gr014_GLOBAL_COMPILE.dta:country:year:other_energycompile_price
aggregate-weighting-denominator: population
infix: withprice
```
