# Olist E-Commerce Sales Analytics Platform

SQL-heavy analytics over the [Olist Brazilian E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
(~100k orders, 9 relational tables), exposed as a FastAPI REST service with
Redis-cached aggregations.

## Stack
- **PostgreSQL** — normalized schema, window functions, CTEs
- **FastAPI** — REST layer over raw SQL (deliberately not an ORM — see below)
- **Redis** — caches expensive aggregation queries
- **Python / pandas** — data loading

## Architecture

```
CSV files → load_data.py → PostgreSQL (9 tables, indexed)
                                  │
                        sql/*.sql (window fns, CTEs)
                                  │
                    FastAPI routers (app/routers/*.py)
                                  │
                    Redis cache (app/cache.py, decorator)
                                  │
                          REST API (/docs for Swagger UI)
                                  │
                     frontend/index.html (Chart.js dashboard)
```

## Setup

```bash
# 1. Start Postgres + Redis
docker-compose up -d

# 2. Install Python deps
pip install -r requirements.txt

# 3. Download the 9 CSVs from Kaggle into ./data/
#    https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

# 4. Load data (schema.sql auto-applies via docker-compose init script)
python load_data.py

# 5. Copy env file and adjust if needed
cp .env.example .env

# 6. Run the API
uvicorn app.main:app --reload

# 7. Open API docs
# http://localhost:8000/docs

# 8. Open the dashboard (just a static file, open directly in browser)
# frontend/index.html
```

## Key design decisions (and why)

**`customer_id` vs `customer_unique_id`.** Olist assigns a new `customer_id`
to every order — the same real person gets a different ID each time they buy.
Cohort retention and RFM analysis both group by `customer_unique_id` instead;
using `customer_id` would make every customer look like a one-time buyer and
silently produce a meaningless retention curve. This was the single most
important bug I had to catch before trusting any of the numbers.

**Raw SQL instead of an ORM.** The point of this project is to demonstrate
SQL (window functions, CTEs, NTILE). An ORM would abstract exactly the part
I'm trying to show. SQLAlchemy Core is used only for connection pooling and
parameterized queries (`text()` with bound params — no string-formatted SQL,
so no SQL injection surface).

**What gets cached vs what doesn't.** `/revenue/trends`, `/cohort/retention`,
`/delivery/delay-vs-review`, and `/sellers/top-by-region` are cached wholesale
via a decorator, since they're full-table aggregations with no per-request
variation that matters much. `/customers/rfm-segments` is different: it's
paginated and filterable, and re-running the `NTILE()` window function (which
must scan the *entire* customer base to assign quartiles) on every page
request would be wasteful. Instead the full scored table is computed once,
cached, and pagination/filtering happens in Python on the cached list.

**Cache invalidation.** There's no automatic invalidation — this is a
read-heavy analytics workload over a dataset that doesn't change at runtime.
`app/cache.py` exposes `invalidate_prefix()` as a manual escape hatch for if
you reload data and need to bust stale results.

**Known data quality issues** (found via `load_data.py`'s sanity checks, not
guessed): a small number of `order_items` reference `product_id`s absent from
the products table, and Olist's `order_reviews` table has a handful of
`review_id` values that repeat across different `order_id`s (hence the
composite primary key). Both are documented rather than silently dropped.

**Dataset limitation worth naming out loud:** ~97% of Olist customers order
exactly once, so cohort retention past month 0 is genuinely low (not a query
bug), and RFM frequency scores are weak signal since most customers tie at
frequency=1. I call this out explicitly rather than presenting misleadingly
smooth-looking segments.

## API Endpoints

| Endpoint | Description | Key SQL concept |
|---|---|---|
| `GET /api/v1/revenue/trends` | Monthly revenue, MoM growth, 3-mo rolling avg | `LAG`, window frame |
| `GET /api/v1/cohort/retention` | Retention % by cohort month × months-since-first-order | Self-join via CTE, `DATE_TRUNC` |
| `GET /api/v1/customers/rfm-segments` | Paginated RFM segments (`?page=&page_size=&segment=`) | `NTILE(4)`, multi-CTE |
| `GET /api/v1/delivery/delay-vs-review` | Review score by delivery-delay bucket + correlation | `CASE` buckets, `CORR()` |
| `GET /api/v1/sellers/top-by-region` | Top-N sellers per state (`?top_n=`) | `RANK()` partitioned |
| `GET /api/v1/products/top-categories-by-region` | Top-N categories per state | `DENSE_RANK()` partitioned |
| `GET /health` | Postgres + Redis connectivity check | — |

Every list response includes `_cache_hit: true/false` so you can see caching
working in real time.

## What I'd do with more time

- Materialized views for the cohort/RFM base tables instead of recomputing on cache miss
- Alembic migrations instead of a single schema.sql
- Auth + rate limiting if this were ever public
- Move the frontend from static Chart.js to a proper React app if the dashboard grew

## Repo structure

```
├── docker-compose.yml       # Postgres + Redis
├── schema.sql                # DDL with indexing rationale in comments
├── load_data.py               # CSV → Postgres loader with sanity checks
├── sql/                        # Standalone .sql files — the actual analysis
│   ├── 01_revenue_trends.sql
│   ├── 02_cohort_retention.sql
│   ├── 03_rfm_segmentation.sql
│   ├── 04_delivery_delay_review.sql
│   └── 05_top_sellers_products.sql
├── app/
│   ├── main.py                 # FastAPI app, health check, error handling
│   ├── config.py                # Settings via pydantic-settings
│   ├── database.py               # Connection pooling, raw SQL runner
│   ├── cache.py                    # Redis caching decorator
│   └── routers/                     # One router per analysis, mirrors sql/
└── frontend/index.html                # Chart.js dashboard, no build step
```
