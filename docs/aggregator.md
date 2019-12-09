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
 - `basename`: Only aggregate results for a given basename (the portion of the filename before `.nc4`, typically copied from the name of the CSVV file).

## Adaptation Costs files

For the adpatation cost files to be generated, the sector needs to be setup so
that the normal output files include a `climtas_effect` variable.  If
this is present, the `generate/cost_curves.R` script will be run to
generate IR-level cost estimates, and then the aggregate script will
aggregate these like it does other files.

For the `cost_curves.R` file to be run, the following libraries need
to be available to the local R program: `pracma`, `ncdf4`, `dplyr`,
`DataCombine`, `zoo`, `abind`, and `rPython`.

## Weighting Schemes

A weighting schemes consists of an expression that can consist of a
known time-varying scaling term, a constant, or products or quotients
of scaling terms and constants.

Possible components:

 - Constant (e.g., 10).
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
