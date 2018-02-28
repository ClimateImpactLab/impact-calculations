The diagnostic run produces a single output set from a single CSVV
file, traditionally for the CCSM4 GCM, under RCP 8.5, socioeconomic
scenario SSP3 under the higher growth model.

The diagnostic run will also produce a set of files useful for running
diagnostics.  These are:

 - `<module>-allpreds`: Contains the covariate values for each region.
   All models are included in the same file, with a `model` column to
   distinguish them.
   
 - `<module>-allcalcs-<basename>`: A file of saved calculations
   produced in the process of generating the result.  The most
   important of these are the response curve coefficients, accounting
   for covariates.

It is treated as a separate kind of batch, called "single".  Since the
content of that batch should only ever hold one file, it will delete
any pre-existing content in the target directory.

One runs the diagnostic system the same way as a normal result generation:

```$ ./generate.sh configs/<CONFIG-FILE>.yml```

where `<CONFIG-FILE>.yml` is a configuration file including the
options below.  The existing collection of diagnostic files are named
`configs/<sector>-diagnostics.yml`.  Configuration settings can also
be overwritten on the command-line, by adding arguments of the form
`--<parameter>=<value>`.

The configuration file for a diagnostic run takes the following settings:

Required:

 - `module`: The sector which defines the various calculations.  These
   must be subdirectories of the `impacts` directory.  For example,
   `mortality`.

 - `mode`: Either `writepolys` or `writesplines`, depending on the
   kind of specification used.  These both tell the system to to run
   in diagnostic mode, and how to generate the resulting files.

 - `outputdir`: A directory where the `single` directory will be
   created.  Typically, this is a versioned subdirectory of
   `/shares/gcp/outputs/<sector>`, such as
   `/shares/gcp/outputs/mortality/impacts-crypto`.  If given a
   relative path, this path is assumed to be a subdirectory of the
   data directory (`/shares/gcp` on Sacagawea).

Optional:

 - `do_only`: A sector-specific named subset of results.  For example,
   the mortality sector supports `interpolation` for the normal set of
   results, `acp` for the ACP specification, and `country` for the
   country-specific models.

 - `do_farmers`: true or false; if true, alternative assumptions of
   adaptation (income-only and no-adaptation) will be generated.

 - `do_historical`: true or false; by default, historical climate
   results are not produced with the diagnostic run, but setting this
   to `true` will produce them.

 - `do_fillin`: true or false; if true, an existing single folder is
   not deleted and only new files are added.

 - `csvvfile`: A path to a CSVV file to be used for the coefficients.
   This can be given as a subpath from the data directory; e.g.,
   `social/parameters/mortality/.../....csv`.

 - `singledir`: The name of the single batch directory; default:
   `single`.

 - `econcovar` and `climcovar`: Covariate averaging specification (see
   Covariate Averaging below).

Note that there is also a script `diagnostic.sh`, which expects to be
given a diagnostics configuration file.  The difference between using
it and using the normal `generate.sh` script is that it will just
produce a result for a single region, and output the result to a local
`temp` directory.

## Covariate Averaging

You can specify in a configuration file the averaging scheme for
climate and economic covariates.  By default, a 13-year Bartlett
kernel is used for economic covariates and a 30-year Bartlett for
climate covariates.  To change these, specify the `class` and `length`
of the new averaging scheme.  For example, to change to a 25-year
running average, you would say,
```
climcovar:
    class: mean
    length: 25
```

The available classes are `mean` (a running average), `median` (a
running median), `bartlett` (a running triangular kernel), and
`bucket` (a running Bayesian updating or exponential kernel).  For the
first three, `length` is the length to the last non-zero term in the
kernel; for the last, it's the decay-rate of the exponential decay.
Always use spaces to indent these parameters.
