OBSOLETE: This has been moved to the impact-calculations wiki.

## Table of contents:

1. Installation
2. Preparing input data
3. Producing results
4. Analyzing results
5. Extensions

## Installation:

If you are on Shackleton, you can skip this step.  However, before
performing any python steps, activate the DMAS virtual environment:

```source /home/jrising/aggregator/env/bin/activate```

You may want to do all of the below within a virtual environment, if
you do not wish or do not have permissions to modify the global python
environment.

-2. DMAS only needs to be installed at `dmas.berkeley.edu`.  See
   `http://meta.aggregator.existencia.org/` for these instructions.

-1. Choose two root directories for the steps below.  One must have a
large amount of space, for data (> 1 TB).  The other should be in a
user directory, and requires little space for code (< 1 GB).  We will
call them $DATA and $CODE, respectively.  These may be the same
directory.  Here is how they are organized on existing systems:
   | =Server=   | =$DATA=         | =$CODE=                              |
   | Shackleton | /shares/gcp     | /home/jrising/aggregator/ext/gcp/src |
   | BRC        | /global/scratch | ~/                                   |
   | OSDC       | /mnt/gcp/data   | ~/                                   |

0. Ensure that you have Python 2.7 installed.
   ```$ python --version```

1. Clone `open-estimate` to $CODE:
   ```$ git clone https://github.com/jrising/open-estimate.git```

2. Follow the steps in the `open-estimate` README to install it.  See
   `http://github.com/jrising/open-estimate`.  You can skip `scipy`
   since we need a specific version of it below.

3. Clone `impact-calculations` to $CODE:
   ```$ git clone git@bitbucket.org:ClimateImpactLab/impact-calculations.git```

4. Install a laundry-list of other packages (now would be a good time
   to set up your virtual environment).
   - netcdf: `apt-get install python-netcdf netcdf-bin libnetcdfc++4 libnetcdf-dev`
     You may need to install
     `https://github.com/Unidata/netcdf4-python` from the source
   - libhdf5 and h5py: `apt-get install libhdf5-serial-dev`; `pip install h5py`
   - cython: `pip install cython`
   - gspread: `pip install gspread`
   - oauth2client v. 1.5.2: `pip install oauth2client==1.5.2`
   - pycrypto: `pip install pycrypto`
   - libffi-dev: `apt-get install libffi-dev`
   - statsmodels: `pip install statsmodels`
   - scipy v. 0.14: `apt-get install libblas-dev liblapack-dev gfortran`; pip install scipy==0.14

5. Copy the main data directory from Norgay or Shackleton into a `$DATA/data` directory:
   ```$ rsync -avz dmas.berkeley.edu:/shares/gcp/data $DATA/data```

6. Copy the BCSD directory from Norgay or Shackleton into a `$DATA/BCSD` directory:
   ```$ rsync -avz dmas.berkeley.edu:/shares/gcp/BCSD $DATA/BCSD```

7. If $CODE and $DATA are not the same directory, create a symbolic
   link from $DATA/data to $CODE/data:
   ```$ ln -s $DATA/data $CODE/data```

## Preparing input data

* The process for preparing most input data is described elsewhere
  (see the socioeconomics wiki).  In particular, the following are
  needed:
  * Data files, stored in the $DATA directory.
  * Impact response functions, stored in DMAS.
  *


See the [Process Document] for a step-by-step process.