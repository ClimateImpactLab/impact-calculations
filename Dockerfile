FROM continuumio/miniconda3:latest

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
ENV PATH /opt/conda/bin:$PATH
ENV PATH /opt/conda/envs/impact-env/bin:$PATH

COPY environment.yml /opt/src/app/environment.yml

RUN bash -c "conda env create -f /opt/src/app/environment.yml \
    && source activate impact-env \
    && conda clean --all \
    && echo "\""conda activate impact-env"\"" >> ~/.bashrc"

COPY . /opt/src/app
RUN bash -c "pip install /opt/src/app"
