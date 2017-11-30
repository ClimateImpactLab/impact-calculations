The aggregator tool is a post-processing tool which operates on
IR-level generated response files.  It generates three kinds of files:

 - `-levels` files, which are scaled versions of the output files,
   using time-varying scaling, at the IR-level.
 - `-aggregated` files, which aggregate IR regions up to higher
   ADM-level, country-level, regional international groupings, and
   globally aggregated outputs.
 - `-costs` files, which estimate the cost bounds for adaptation.

If the raw outputs are *y_it*, then the scaling scheme in the levels
files produces *w_it y_it*, and the aggregation system computes
*(sum_i w_it y_it) / sum_i w_it*.

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
   and `aggregate-weighting-denominator`.
   
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
 - Term ` * ` Term: The product of two terms (can be chained).
 - Term ` / ` Term: The quotient of two terms (can be chained).  Terms
   are computed sequentially, so *(a b) / (c d)* should be described
   as `a * b / c / d`.

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
