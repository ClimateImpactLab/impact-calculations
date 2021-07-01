## Table of contents:

1. Installation
2. Preparing input data
3. Producing results
4. Analyzing results

## Installation:

1. Prepare your data directory.

The data directory contains input files for the projection system, and
generally is where output files are written. The necessary inputs
differ depending on the projection being performed, but generally
consist of projection climate data and socioeconomic data, and common
region definitions.

This directory can be in any accessible location on the computer. Its
location will be used in a later step.

2. Prepare the software environment.

The easiest way to install the necessary libraries is to use the
`risingverse` conda environment, available at
https://github.com/ClimateImpactLab/risingverse/

Instructions for installing it are provided in the README of that
repository.

Alternatively, you can install the necessary libraries by hand. The
remaining text in this section provides information on doing that. If you do this, we recommend that you start by creating a virtual environment to keep python packages separate across projects.

First, make a new virtual environment directory, execuing from your project directory:
```
python -m venv env
```

This will create a directory `env` within the current directory.

Now, activate the virtual environment to "enter" its set of packages:
```
source env/bin/activate
```

Now, all of your `pip` commands will add packages just to the environment.  Drop all `--user` arguments from the `pip` commands below.
You will need to do this last line every time you want to use the system.

Next, install a laundry-list of public packages, if they aren't already installed (use `--user` for pip commands on a shared computer):
    - numpy
    - netcdf: `apt-get install python-netcdf netcdf-bin libnetcdfc++4 libnetcdf-dev`.
       You may need to install
       `https://github.com/Unidata/netcdf4-python` from the source
    - libhdf5 and h5py: `apt-get install libhdf5-serial-dev`; `pip install h5py`
    - metacsv: `pip install metacsv`
    - libffi-dev: `apt-get install libffi-dev`
    - statsmodels: `pip install statsmodels`
    - scipy: `apt-get install libblas-dev liblapack-dev gfortran`; `pip install scipy`
    - xarray: `pip install xarray==0.10.9`
    - pandas: `pip install pandas==0.25.3`

Clone `open-estimate` to your project directory:
   ```$ git clone https://github.com/ClimateImpactLab/open-estimate.git```

Install it: 
```
$ cd open-estimate
$ python setup.py develop --user
$ cd ..
```

Similarly, install `impactlab-tools` and `impact-common`:
```
$ git clone https://github.com/ClimateImpactLab/impactlab-tools.git
$ cd impactlab-tools
$ python setup.py develop --user
$ cd ..
$ git clone https://github.com/ClimateImpactLab/impact-common.git
$ cd impact-common
$ python setup.py develop --user
$ cd ..
```

3. Install the `impact-calculations` repository.

Clone `impact-calculations` to your project directory:
   ```$ git clone git@bitbucket.org:ClimateImpactLab/impact-calculations.git```

The `impact-calculations` code needs to know where to find the data directory from step one, and this information is given in a file named `server.yml` in the directory that contains `impact-calculations`.

The contents of this file should be:
```
shareddir: <full-path-to-data-directory>
```

## Producing results

Diagnostic, median, and Monte Carlo results are produced by calling `./generate.sh CONFIG.yml`.  The `CONFIG.yml` files are stored in the `configs/` directory.  You may optionally put a number after this command, to spawn that many background processes.  Here are example commands:

* Generate a diagnostic collection of predictors and outputs for each region and year:
  ```$ ./generate.sh configs/mortality-diagnostic.yml```

* Generate results for the median quantile of the econometric distributions:
  ```$ ./generate.sh configs/mortality-median.yml```

* Generate results performing a Monte Carlo across econometric uncertainty with 10 processes:
  ```$ ./generate.sh configs/mortality-montecarlo.yml 10```

## Analyzing results

### Timeseries results

* Clone the `prospectus-tools` repository on a machine with results:
  ```$git clone https://github.com/jrising/prospectus-tools.git tools```

* Make any changes to the `tools/gcp/extract/configs/timeseries.yml` file, following the information in the `README.md` and `config-dogs.md` in `tools/gcp/extract`.

* From the `tools/gcp/extract` directory, extract all timeseries available for each RCP and SSP:
  ```$ python quantiles.py configs/timeseries.yml RESULT-PREFIX```
    - `RESULT-PREFIX` is a prefix in the filenames of the `.nc4` result files.  It might be (for example) each of the following:
        - `interpolated_mortality_all_ages-histclim` or `interpolated_mortality_all_ages-histclim-aggregated`: historical climate impacts, non-aggregated and aggregated.
        - `interpolated_mortality_all_ages` or `interpolated_mortality_all_ages-aggregated`: normal full-adaptation impacts
        - `interpolated_mortality_ASSUMPTION_all_ages-aggregated` or `interpolated_mortality_ASSUMPTION_all_ages-aggregated`: partial adaptation, where `ASSUMPTION` is `incadapt` or `noadapt`.
        - `interpolated_mortality_all_ages-costs` or `interpolated_mortality_all_ages-costs-aggregated`: cost estimates (combine with `VARIABLE` optional argument).
