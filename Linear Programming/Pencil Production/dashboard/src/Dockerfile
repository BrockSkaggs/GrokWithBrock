FROM python:3.11.7-bullseye
WORKDIR /app
RUN apt-get update
RUN apt-get install -y glpk-utils libglpk-dev glpk-doc
COPY . .
RUN pip3 install -r requirements.txt
ENTRYPOINT [ "gunicorn", "--bind", "0.0.0.0:8050", "app:server" ]