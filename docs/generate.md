# Options for the generate system

The generate system takes a configuration file, typically stored in
`configs/`.  Below are additional configuration options that can be
included in the generate configuration file.

 - `only-rcp` or `rcp`: The name of an RCP to run (rather than all available
   RCPs), in the form `rcp26`.
 - `only-models`: Either a single GCM name or a list of allowed GCMs.
 - `include-patterns`: true or false; produce results for pattern models
 - `only-ssp` or `ssp`: The name of an SSP to use (e.g., `SSP3`), or a list of SSPs.

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
