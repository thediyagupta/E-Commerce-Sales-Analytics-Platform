![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue?logo=postgresql)
![Redis](https://img.shields.io/badge/Redis-7-red?logo=redis)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?logo=docker)



# E-Commerce Sales Analytics Platform

An end-to-end analytics platform built using **PostgreSQL, FastAPI, Redis, Docker, and Python** to process and analyze the Olist Brazilian E-Commerce dataset. The platform exposes REST APIs and an interactive dashboard for business intelligence, including revenue trends, customer segmentation, cohort retention, seller performance, and delivery analytics.

## Dashboard

![Dashboard](assets/dashboard.png)

## API Documentation

### Revenue & Cohort APIs

![Swagger 1](assets/swagger_1.png)

### Customer & Seller APIs

![Swagger 2](assets/swagger_2.png)

### Delivery APIs

![Swagger 3](assets/swagger_3.png)

## Features

- Automated ETL pipeline for ingesting 1.18M+ records from the Olist dataset
- Normalized PostgreSQL database with 9 relational tables
- Advanced SQL analytics using CTEs, window functions, aggregations, and cohort analysis
- Customer RFM segmentation with window functions (NTILE)
- FastAPI backend exposing 6+ REST APIs
- Redis-backed caching for expensive analytical queries
- Interactive Chart.js dashboard consuming live API endpoints
- Dockerized deployment with PostgreSQL and Redis

## Tech Stack

| Category | Technologies |
|----------|--------------|
| Backend | FastAPI, Python |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Caching | Redis |
| Data Processing | Pandas |
| Containerization | Docker, Docker Compose |
| Frontend | HTML, CSS, JavaScript, Chart.js |

## Architecture

           Kaggle Olist Dataset
                   │
                   ▼
          Python ETL (Pandas)
                   │
                   ▼
        PostgreSQL Database
                   │
          SQLAlchemy Queries
                   │
                   ▼
             FastAPI Backend
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
   Redis Cache         REST API Endpoints
        │                     │
        └──────────┬──────────┘
                   ▼
         Chart.js Dashboard

## Database Design

The platform stores data in a normalized PostgreSQL schema comprising:

- Customers
- Orders
- Order Items
- Products
- Sellers
- Payments
- Reviews
- Geolocation
- Product Category Translation

The schema uses primary keys, foreign keys, and indexes to optimize analytical workloads.


## Performance Benchmarks

| Benchmark | Result |
|-----------|--------|
| Average API Response (Redis Cache) | **13.2 ms** |
| Average API Response (No Cache) | **210.1 ms** |
| API Latency Reduction | **93.7%** |

## Installation

```bash
git clone <repository-url>

cd ecommerce-analytics

docker compose up -d

python load_data.py

uvicorn app.main:app --reload
```


## API Endpoints

| Endpoint | Description |
|----------|-------------|
| /api/v1/revenue/trends | Monthly revenue analysis |
| /api/v1/customers/rfm-segments | Customer RFM segmentation |
| /api/v1/cohort | Cohort retention analysis |
| /api/v1/sellers | Top sellers by region |
| /api/v1/delivery | Delivery delay vs review score |

## Future Improvements

- JWT Authentication
- CI/CD Pipeline
- Kubernetes deployment
- Scheduled ETL jobs
- Cloud deployment (AWS/GCP/Azure)
