Outputs are organized into trees with the following contents:

Level 1, `outputdir`: This is the root directory for a sector-specific and
version-specific set of outputs.

Level 2, batches: Each batch contains all of the following
GCM-specific sets of files, but a different set of assumptions about
the economic uncertainty.  `median` and `single` assume the median
across the economic uncertainty, with `single` having only a single
result set but additional diagnostic outputs.  `batch*` contain
parallel sets of results to `median`, but where each is a specific
Monte Carlo draw.

Level 3, RCPs: Each folder is a climate scenario.

Level 4, GCMs: Each folder is a climate model.

Level 5, IAMs: Each folder is an economic model.  We group economic
models into a `high` estimate of GDP and a `low` estimate (and name
the folders accordingly).  The `high` estimates are from the OECD
Env-Growth model, and the `low` estimates are from the `IIASA GDP`,
but both use population projections that are the average of these two
models.

Level 6, SSPs: Each folder is an economic scenario, described as a
shared socioeconomic pathway.

Level 7, `targetdir`: This folder contains all of the actual results,
mostly in the form of NetCDF4 files.  A `pvals.yml` file describes the
assumptions around economic uncertainty, and `status-*.txt` which
logs current and past actions.

## Other configuration options

Below are additional configuration options that can be included in the
generate configuration file.

 - only-models: a list of allowed GCMs
 - only-rcp: a list of allowed RCPs
 - include-patterns: true or false; produce results for pattern models
