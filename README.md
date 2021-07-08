# impact-calculations

`impacts-calculations` contains the code necessary to generate, aggregate, and analyze physical impacts from econometric response functions.

The package can be installed locally as a python package but it also includes several additional scripts.

Contents:

* adaptation: Interpolation and adaptation logic
* analysis: Post-processing analysis (mostly R)
* climate: Interface to the climate data
* computer: Tools that use `computer` to run, monitor, and collect results
* datastore: Interfaces to the input datasets
* docs: Various documentation-- should probably be moved!
* generate: Top-level functions for climate result-making
* helpers: Helper code
* impacts: Definitions of calculation
* interpolate: Used by Chicago to make `.csvv` file
* shortterm: Top-level functions for forecast result-making
* tests: Unit tests

## Installation

Clone the repository to a local directory and install the python package components with

```
pip install -e .
```

Although the code in the repo can be installed as a Python package, there are additional bits of supplimental code and scripts that are hard-coded to the local directory and so will only function from the root directory of this repository.

Generating projections, diagnostics, and projection aggregations depends on additional input files in a particular directory structure. Users can point to the root of this directory with the `IMPERICS_SHAREDDIR` environment variable. For example, if the root of the directory is `/shares/gcp` we can append
```
# Configs for impact projection runs
export IMPERICS_SHAREDDIR=/shares/gcp
```
to `~/.bashrc`.

For more details on installation, or to install the repository in a
way more conducive to doing development work on the projection system,
see `docs/install.md`.

## Projections with the `imperics` CLI

The installed python package includes a command-line interface (CLI) to handle projection generation, diagnostics, and aggregation. This is done with `imperics generate`, `imperics diagnostic` and `imperics aggregate`. All commands accept a YAML run configuration file as the first argument. For basic options, see `imperics --help`, or use `--help` with any `imperics` subcommand.

## Support

See `docs/` for additional documentation.
