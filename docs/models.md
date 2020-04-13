This document describes the functional organization used to describe
projection models. It is expected that most models will not need to be
written using the structures described here. Instead, the Imperics
configuration system can be used, as described by `docs/imperics.md`.

Projection models are described in modules, typically organized into
subdirectories of the `impacts` subdirectory. These modules should
expose the following functions:

 - `preload()`: Function called once before individual bundles are
   produced, to load any necessary information into memory.
   
 - `get_bundle_iterator(config)`: Returns an iterator of weather
   bundles, with all necessary weather.
   
 - `produce(targetdir, weatherbundle, economicmodel, pvals, config,
   push_callback=None, suffix='', profile=False, diagnosefile=False)`:
   Produce all files for a given bundle of input data, into the
   specified `targetdir` directory.

The `produce` function generally has the following standard workflow:

1. Find associated CSVVs. If there are multiple, iterate through each one.
2. Collapse the parameter data based on the randomization information
   in `pvals`.
3. For each adaptation assumption (full, income-only, and
   no-adaptation), and typically just full if
   `weatherbundle.is_historical()`:
   
   a. Check if the file has already been generated, and skip
   otherwise.
   
   b. Call `calculation, dependencies, baseline_get_predictors =
   caller.call_prepare_interp(csvv, module, weatherbundle,
   economicmodel, pvals, config)` to set up the calculation.
   
   c. Call `effect.generate(targetdir, basename, weatherbundle,
   calculation, description, dependencies, config, push_callback,
   diagnosefile)` to generate the results.
   
Above `module` is used to refer to a python model for each
specification. This should exponse the function
`prepare_interp_raw(csvv, weatherbundle, economicmodel, qvals, farmer,
config)` to create the calculation. Other possible functions are
supported, but generally no longer used.

This function also tends to have a standard workflow:

1. Load the covariates. A single Covariator object is constructed.
3. Collect baseline data, if it is necessary for any clipping.
2. Construct the basic CurveGenerator for the specification,
   typically a CurveGenerator described in `adaptation/curvegen_known`
   or `adaptation/curvegen_arbitrary`.
4. Apply any curve generator transformations, reflecting clipping.
5. Wrap the curve generator in a `FarmerCurveGenerator` to handle
   adaptation, passing in the covariator.
6. Construct a Calculation object which transforms and combines data
   coming from the CurveGenerators. Return this object.
