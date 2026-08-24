FROM python:3.13-bookworm

WORKDIR /code

RUN apt-get update
#Reference: https://askubuntu.com/questions/349582/installing-and-running-glpk
RUN apt-get install -y glpk-utils libglpk-dev glpk-doc

COPY ./requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ./data ./data
COPY ./src ./src

RUN mkdir /code/data/cache

EXPOSE 8050
WORKDIR /code/src
ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:8050", "app:server"]
