FROM continuumio/miniconda3:latest

WORKDIR /opt/src/app
COPY . .

RUN bash -c "conda install anaconda-client \
    && conda env create ClimateImpactLab/risingverse-py27 \
    && source activate risingverse-py27 \
    && conda clean --all \
    && pip install git+https://github.com/ClimateImpactLab/open-estimate.git \
    && pip install git+https://github.com/ClimateImpactLab/impact-common.git \
    && pip install -e ."

ENTRYPOINT ["/opt/conda/envs/risingverse-py27/bin/imperics"]
