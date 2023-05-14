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
Chek if every container is running
```
docker-ps
```
Imagen explicando porque cli no inicia con compose up y porque hay q correrlo por separado

