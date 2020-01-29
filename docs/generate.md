# Options for the generate system

The generate system takes a configuration file, typically stored in
`configs/`.  Below are additional configuration options that can be
included in the generate configuration file.

 - `only-rcp` or `rcp`: The name of an RCP to run (rather than all available
   RCPs), in the form `rcp26`.
 - `only-models`: Either a single GCM name or a list of allowed GCMs.
 - `include-patterns`: true or false; produce results for pattern models
 - `only-ssp` or `ssp`: The name of an SSP to use (e.g., `SSP3`), or a list of SSPs.
 - `only-iam` or `iam`: The name of an IAM to use (e.g., `high`).
 - `timeout`: The number of hours to allow the process to work, before
   considering a directory abandoned (default: 12).

# Options within a target

 - `do_historical`: true or false; by default, historical climate
   results are not produced with the diagnostic run, but setting this
   to `true` will produce them.

 - `do_farmers`: true, false, or 'always'; if true, alternative
   assumptions of adaptation (income-only and no-adaptation) will be
   generated.  If 'always', alternative adaptation assumptions will be
   calculated even with historical climate.

 - `csvvfile`: A path to a CSVV file to be used for the coefficients.
   This can be given as a subpath from the data directory; e.g.,
   `social/parameters/mortality/.../....csv`.
 
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

