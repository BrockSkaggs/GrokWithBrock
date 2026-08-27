FROM jupyter/minimal-notebook:x86_64-python-3.11
USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends coinor-cbc coinor-libcbc-dev && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /code
COPY requirements.txt .
RUN pip3 install -r requirements.txt
ENTRYPOINT [ "jupyter", "lab", "--allow-root" ]


#Run Command
#docker run -p 8888:8888 --mount "type=bind,src=$PWD,target=/code" jupyter_lp_single
