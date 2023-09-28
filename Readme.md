# Scraping & ETL pipeline with Selenium, Prefect and Docker

## About
Personal project to understand and put in practice docker concepts and workflow orchestation with various tools.

Postgres is used as database to store records extracted from a dynamic webpage using scraping concepts and tools. Prefect works orchestrating the pipeline, everything connected through docker containers.

Pipeline Architecture:
![kBB2fF.png](https://i1.lensdump.com/i/kBB2fF.png)

## Idea
The records provided by a [webpage](https://www.bancoprovincia.com.ar/cuentadni/contenidos/cdniBeneficios/), it contains shops in Buenos Aires province they offer a discount to the users of certain Bank. each record has its own info and a location button. Problem is, not every record has the button avaible. I made a script to obtains the missing data(if shop info is complete) and stores the fullfilled table to a database.

## Prerequisites
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/)

## Set up
Clone the repo
```
git clone https://github.com/franciscodevs/etl-project.git
```
Create and start containers
```
docker-compose up -d 
```
Run CLI container to interact with the pipeline

**Note:** This containers needs to run separately with ```--rm``` wich is used to remove the container once is stopped. 
```
docker-compose run --rm cli
```
Chek in another terminal if every container is running
```
docker-ps
```

![6gOXQz.png](https://i.lensdump.com/i/6gOXQz.png)

- ![#00ff00](https://via.placeholder.com/15/00ff00/000000?text=+) `Command line Container`
- ![#ed0124](https://via.placeholder.com/15/ed0124/000000?text=+) `Environment Container (Prefect, PostgreSQL, ChromeDriver)`

Command line interacts with prefect to run flows, deployments, etc. 

## Pipeline Overview
This pipeline consists of the following steps:

1. **Initialization**: Initialize a Chrome WebDriver instance for web scraping.
2. **Data Extraction**: Load web pages, extract table data, and concatenate the results.
3. **Geocoding**: Geocode adresses in the dataset using the GoogleV3 geocoder.
4. **Data Ingestion**: Create a PostgreSQL table and ingest the geocoded data.
