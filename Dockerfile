FROM continuumio/miniconda3:latest

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
ENV PATH /opt/conda/bin:$PATH
ENV PATH /opt/conda/envs/risingverse-py27/bin:$PATH

WORKDIR /opt/src/app
COPY . .

RUN bash -c "conda install anaconda-client \
    && conda env create ClimateImpactLab/risingverse-py27 \
    && source activate risingverse-py27 \
    && conda clean --all \
    && pip install git+https://github.com/ClimateImpactLab/open-estimate.git \
    && pip install git+https://github.com/ClimateImpactLab/impact-common.git \
    && pip install -e . \
    && echo "\""conda activate risingverse-py27"\"" >> ~/.bashrc"

CMD [ "/bin/bash" ]
