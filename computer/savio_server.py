# Setup

"""
rsync -avz /shares/gcp/climate/BCSD/aggregation/cmip5/IR_level/ jrising@dtn.brc.berkeley.edu:/global/scratch/jrising/climate/BCSD/aggregation/cmip5/IR_level/

rsync -avz /shares/gcp/social/ jrising@dtn.brc.berkeley.edu:/global/scratch/jrising/social/

ssh jrising@hpc.brc.berkeley.edu
mkdir gcp
cd gcp
git clone https://jrising@bitbucket.org/ClimateImpactLab/socioeconomics.git src

git clone https://github.com/jrising/open-estimate.git

module load python/2.7.8
module load virtualenv

virtualenv env
source env/bin/activate

cd open-estimate
python setup.py develop

cd ../src

module load numpy
module load hdf5
module load netcdf
module load scipy

module unload intel
module load gcc

pip install netCDF4
pip install gspread

pip install oauth2client==1.5.2
pip install pycrypto
pip install pyyaml
pip install statsmodels

pip install scipy==0.16.1
module unload scipy
module load numpy

"""
# Restart

"""
module load python/2.7.8
module load virtualenv

cd gcp/open-estimate
git pull

cd ../src
git stash
git pull
git stash apply

module load python/2.7.8

cd ~/gcp/src
source ../env/bin/activate

module load numpy
module load hdf5
module load netcdf

python -m generate.montecarlo /global/scratch/jrising/outputs

## Send

----------------------------- /global/software/sl-6.x86_64/modfiles/tools -----------------------------
allinea/6.0          ghostscript/9.04     matlab/R2015a        serf/1.2.1
apr/1.4.8            git/2.2.2            mercurial/2.0.2      subversion/1.8.3
apr-util/1.5.2       glib/2.32.4          ncl/6.1.2            texinfo/5.2
atk/2.4.0            gnuplot/4.6.0        ncview/2.1.2         texlive/2013
bazel/0.2.0          grace/5.1.22         octave/3.8.1         tmux/1.8
binutils/2.26        graphviz/2.28.0      openmotif/2.3.3      valgrind/3.7.0
cairo/1.12.8         gtk+/2.24.13         p7zip/9.20.1         visit/2.10.0
cmake/3.2.2          imagemagick/6.8.8-10 pango/1.30.1         vmd/1.9.1
cscope/15.8          lftp/4.6.0           paraview/3.12.0      yt/2.3
ctags/5.8            libevent/2.0.21      pigz/2.3.1           zsh/5.0.0
doxygen/1.7.6.1      libffi/3.0.11        pixman/0.28.0
emacs/24.1           lz4/1.5.0            pvm/3.4.6
gdk-pixbuf/2.26.0    matlab/R2014a        qt/4.8.0

----------------------------- /global/software/sl-6.x86_64/modfiles/langs -----------------------------
cuda/6.5                      intel/2015.6.233              python/2.7.8
cuda/7.5.18                   intel/2016.1.150              python/3.2.3
gcc/4.4.7(default)            java/1.8.0_05(default)        r/3.1.1
gcc/4.8.5                     julia/0.3.9
intel/2013_sp1.4.211(default) python/2.6.6(default)

--------------------- /global/software/sl-6.x86_64/modfiles/intel/2013_sp1.4.211 ----------------------
acml/5.3.1-intel          hdf5/1.8.13-intel-p       netcdf/4.3.2-intel-s
antlr/2.7.7-intel         hdf5/1.8.13-intel-s       openmpi/1.6.5-intel
atlas/3.10.2-intel        ipp/2013_sp1.4.211        pdtoolkit/3.20-intel
berkeley_upc/2.18.2-intel lapack/3.5.0-intel        scalapack/2.0.2-intel
boost/1.56.0-intel        mkl/2013_sp1.4.211        tau/2.23.2b3-intel
fftw/2.1.5-intel          nco/4.4.6-intel-p         tbb/2013_sp1.4.211
fftw/3.3.4-intel          nco/4.4.6-intel-s         udunits/2.2.17-intel
gsl/1.16-intel            netcdf/4.3.2-intel-p

------------------------- /global/software/sl-6.x86_64/modfiles/python/2.7.8 --------------------------
apptools/4.2.1      markupsafe/0.23     pandas/0.14.1       pyparsing/2.0.2     tables/3.1.1
configobj/5.0.6     matplotlib/1.4.0    pil/1.1.7           python-dateutil/2.2 theano/0.7.0
cython/0.21         mayavi/4.3.2        pip/1.5.6           pytz/2014.7         tornado/4.0.2
decorator/3.4.0     mock/1.0.1          pkgconfig/1.1.0     pyzmq/14.3.1        traits/4.5.0
distribute/0.7.3    mpi4py/1.3.1        py2cairo/1.10.0     scikit-image/0.10.1 traitsui/4.4.0
docutils/0.12       mpmath/0.18         pydot/1.0.28        scikit-learn/0.15.2 virtualenv/1.11.6
envisage/4.4.0      networkx/1.9.1      pyface/4.4.0        scipy/0.14.0        vtk/5.10.1
h5py/2.5.0          nose/1.3.4          pygments/1.6        setuptools/6.0.2    wxpython/3.0.1.1
ipython/2.3.0       numexpr/2.4         pygobject/2.28.6    six/1.8.0
jinja2/2.7.3        numpy/1.9.0         pygtk/2.24.0        sphinx/1.2.3
