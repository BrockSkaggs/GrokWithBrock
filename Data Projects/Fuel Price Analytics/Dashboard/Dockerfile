FROM python:3.11-slim

WORKDIR /code


COPY ./requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src ./src
EXPOSE 8050
CMD ["python", "./src/app.py"]


#Run command
#Bind GasScrapeTest to /code
#Set environment variable ENV PIP_ROOT_USER_ACTION=ignore


#docker run -d -p 8050:8050 -p 8049:8049 --mount type=bind,source="C:\Users\brock\Desktop\GasScrapeTest",target="/code" --name scrape_dash_dev gas-scrape-dev:latest