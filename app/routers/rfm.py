from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.database import get_db, run_query
from app.cache import cached

router = APIRouter(prefix="/api/v1/customers", tags=["rfm"])

RFM_BASE_SQL = """
WITH customer_orders AS (
    SELECT
        c.customer_unique_id,
        o.order_id,
        o.order_purchase_timestamp,
        oi.price + oi.freight_value AS order_value
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
),
rfm_base AS (
    SELECT
        customer_unique_id,
        (SELECT MAX(order_purchase_timestamp) FROM customer_orders)::DATE
            - MAX(order_purchase_timestamp)::DATE AS recency_days,
        COUNT(DISTINCT order_id) AS frequency,
        SUM(order_value) AS monetary
    FROM customer_orders
    GROUP BY customer_unique_id
),
rfm_scored AS (
    SELECT
        customer_unique_id,
        recency_days,
        frequency,
        monetary,
        NTILE(4) OVER (ORDER BY recency_days ASC) AS r_score,
        NTILE(4) OVER (ORDER BY frequency DESC) AS f_score,
        NTILE(4) OVER (ORDER BY monetary DESC) AS m_score
    FROM rfm_base
)
SELECT
    customer_unique_id,
    recency_days,
    frequency,
    monetary,
    r_score, f_score, m_score,
    (r_score + f_score + m_score) AS rfm_total,
    CASE
        WHEN r_score = 1 AND f_score = 1 AND m_score = 1 THEN 'Champions'
        WHEN r_score <= 2 AND f_score <= 2 THEN 'Loyal Customers'
        WHEN r_score = 1 AND f_score >= 3 THEN 'New / Promising'
        WHEN r_score >= 3 AND f_score <= 2 THEN 'At Risk'
        WHEN r_score = 4 AND f_score = 4 THEN 'Lost'
        ELSE 'Needs Attention'
    END AS segment
FROM rfm_scored
"""


@cached(prefix="rfm_full_table", ttl=3600)
async def _compute_rfm_table(db: Session):
    """Runs the expensive NTILE computation once and caches the full
    result set. Pagination/filtering happens in Python on the cached
    list, so we don't re-run window functions over the whole customer
    base on every page request."""
    rows = run_query(db, RFM_BASE_SQL)
    return {"rows": rows}


@router.get("/rfm-segments")
async def get_rfm_segments(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    segment: str | None = Query(None, description="Filter by segment name, e.g. 'Champions'"),
    db: Session = Depends(get_db),
):
    """Paginated, filterable RFM customer segmentation."""
    try:
        cached_result = await _compute_rfm_table(db)
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    rows = cached_result["rows"]

    if segment:
        rows = [r for r in rows if r["segment"].lower() == segment.lower()]

    total_count = len(rows)
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    if page > total_pages and total_count > 0:
        raise HTTPException(status_code=404, detail=f"Page {page} exceeds total_pages {total_pages}")

    start = (page - 1) * page_size
    end = start + page_size

    return {
        "page": page,
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": total_pages,
        "data": rows[start:end],
    }
