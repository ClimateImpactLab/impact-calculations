FROM continuumio/miniconda3:latest

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
ENV PATH /opt/conda/bin:$PATH
ENV PATH /opt/conda/envs/risingverse/bin:$PATH

WORKDIR /opt/src/app
COPY . .

RUN bash -c "conda install anaconda-client \
    && conda env create ClimateImpactLab/risingverse \
    && source activate risingverse \
    && conda clean --all \
    && pip install git+https://github.com/ClimateImpactLab/open-estimate.git \
    && pip install git+https://github.com/ClimateImpactLab/impact-common.git \
    && pip install -e . \
    && echo "\""conda activate risingverse"\"" >> ~/.bashrc"

CMD [ "/bin/bash" ]
