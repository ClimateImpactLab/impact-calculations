FROM continuumio/miniconda3:latest

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
ENV PATH /opt/conda/bin:$PATH
ENV PATH /opt/conda/envs/risingverse/bin:$PATH

RUN bash -c "conda install anaconda-client \
    && conda env create ClimateImpactLab/risingverse \
    && source activate risingverse \
    && conda clean --all \
    && echo "\""conda activate risingverse"\"" >> ~/.bashrc"

COPY . /opt/src/app
RUN bash -c "pip install /opt/src/app"
