## Table of contents:

1. Installation
2. Preparing input data
3. Producing results
4. Analyzing results

## Installation:

If you are working on Sacagawea, you can skip steps -1 and 0.

-1. Choose the root directories for data with > 1 TB space.  Here is how they are organized on existing systems:

   | Server | $DATA |
   | --- | --- |
   | Shackleton | /shares/gcp |
   | BRC | /global/scratch/USERNAME |
   | OSDC | /mnt/gcp/data |

0. Ensure that you have Python 2.7 and the `numpy` and `scipy` libraries installed
```
$ python --version
$ pip install numpy
$ pip install scipy
```

1. Clone `open-estimate` to your project directory:
   ```$ git clone https://github.com/ClimateImpactLab/open-estimate.git```

2. Install it: 
```
$ cd open-estimate
$ python setup.py develop --user
$ cd ..
```

3. Similarly, install `impactlab-tools` and `impact-common`:
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

4. Clone `impact-calculations` to your project directory:
   ```$ git clone git@bitbucket.org:ClimateImpactLab/impact-calculations.git```

5. Install a laundry-list of other packages, if they aren't already installed (use `--user` for pip commands on a shared computer):
    - netcdf (if not on Sacagawea): `apt-get install python-netcdf netcdf-bin libnetcdfc++4 libnetcdf-dev`.
       You may need to install
       `https://github.com/Unidata/netcdf4-python` from the source
    - libhdf5 and h5py (if not on Sacagawea): `apt-get install libhdf5-serial-dev`; `pip install h5py`
    - metacsv: `pip install metacsv`
    - libffi-dev (if not on Sacagawea): `apt-get install libffi-dev`
    - statsmodels: `pip install statsmodels`
    - scipy: `apt-get install libblas-dev liblapack-dev gfortran` (if not on Sacagawea); pip install scipy

6. Copy the necessary data from Sacagawea into your `$DATA` directory, if you are not on Sacagawea:
   ```$ rsync -avz sacagawea.gspp.berkeley.edu:/shares/gcp/social $DATA/social```
   ```$ rsync -avz sacagawea.gspp.berkeley.edu:/shares/gcp/regions $DATA/regions```
   ```$ rsync -avz sacagawea.gspp.berkeley.edu:/shares/gcp/climate $DATA/climate```
   (you probably only want to copy over a subset of the data in `climate`.)

7. The `impact-calculations` code needs to know where to find the `$DATA` directory and is given this information by placing a file named `server.yml` in the directory that contains `impact-calculations`.  Look at one of the files `impact-calculations/configs/servers-*.yml` and copy it to the directory containing `impact-calculations`, giving it the name `server.yml`.

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
