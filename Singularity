Bootstrap: docker

From: continuumio/miniconda3

%files
    . .

%environment
    export LANG=C.UTF-8 
    export LC_ALL=C.UTF-8
    export PATH /opt/conda/bin:$PATH

%post
    conda install anaconda-client
    conda env create ClimateImpactLab/risingverse
    source activate risingverse
    conda clean --all
    pip install -e .
    echo "conda activate risingverse" >> ~/.bashrc

%runscript
    exec "$@"
