The single.py script produces an individual result and aggregates it.  The command to run it is
```
$ python -m generate.single CONFIG.yml
```

The configuration files for the single script are different from those
used by the generate script.  See `configs/mortality-single.yml` for
an example.  The available options are shown below.

## Options for Single Configurations

The following options are available for a configuration file for the
single (single.py) run:

** Required Configuration Parameters **

 - `module`: The name of the python module which generates the result.
   This is generally a python file or a specification configuration
   file, contained under the `impacts/` directory.  This corresponds
   to the module selected in the `allmodels.py` script, for those
   sectors set up for median runs.  To run the specification in
   `impacts/mortality/ols_polynomial.py`, use the module name
   `mortality.ols_polynomial`.
 - `targetdir`: A local directory where the output will be written.
 - `pvals`: A probability specification, which may be `median`,
   `montecarlo`, or a constant quantile value, like `.25`.
 - `rcp`: The RCP to use.  See the corresponding directory level in
   `outputs.md`.
 - `gcm`: The GCM to use.  See the corresponding directory level in
   `outputs.md`.
 - `iam`: The IAM to use.  See the corresponding directory level in
   `outputs.md`.
 - `ssp`: The SSP to use.  See the corresponding directory level in
   `outputs.md`.
 - `climate`: The necessary climate data.  This should correspond to
   the climate data in the `allmodels.get_bundle_iterator` function.
   A documentation file describing the options available for it is
   forthcoming.
 - `csvvpath`: The path to a CSVV file, either as an absolute path or a
   path relative to `/shares/gcp/`.
 - `adaptation`: Specify a particular adaptation assumption.  May be
   `fulladapt`, `incadapt`, or `noadapt`.
 - `weighting`: Specify the weighting scheme for aggregation.  See
   `aggregator.md` for the available weighting schemes.

** Optional configuration parameters **

 - `csvvsubset`: If the CSVV file contains multiple sets of parameters
   in one file (e.g., as done for age-specific models for mortality),
   this specifies in quotes the 1-indexed locations of the parameters
   to be used.
   