from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.database import get_db, run_query
from app.cache import cached

router = APIRouter(prefix="/api/v1/delivery", tags=["delivery"])

DELAY_BUCKET_SQL = """
WITH delivery_facts AS (
    SELECT
        o.order_id,
        r.review_score,
        EXTRACT(DAY FROM (o.order_delivered_customer_date - o.order_estimated_delivery_date)) AS delay_days
    FROM orders o
    JOIN order_reviews r ON o.order_id = r.order_id
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_estimated_delivery_date IS NOT NULL
),
bucketed AS (
    SELECT
        review_score,
        delay_days,
        CASE
            WHEN delay_days <= -7 THEN '1. Early (7+ days)'
            WHEN delay_days > -7 AND delay_days <= 0 THEN '2. On time / slightly early'
            WHEN delay_days > 0 AND delay_days <= 3 THEN '3. Late (1-3 days)'
            WHEN delay_days > 3 AND delay_days <= 7 THEN '4. Late (4-7 days)'
            ELSE '5. Very late (7+ days)'
        END AS delay_bucket
    FROM delivery_facts
)
SELECT
    delay_bucket,
    COUNT(*) AS num_orders,
    ROUND(AVG(review_score), 2) AS avg_review_score,
    ROUND(AVG(delay_days), 1) AS avg_delay_days,
    ROUND(100.0 * SUM(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_low_reviews
FROM bucketed
GROUP BY delay_bucket
ORDER BY delay_bucket;
"""

CORRELATION_SQL = """
SELECT ROUND(CORR(
    EXTRACT(DAY FROM (o.order_delivered_customer_date - o.order_estimated_delivery_date))::NUMERIC,
    r.review_score
)::NUMERIC, 4) AS delay_review_correlation
FROM orders o
JOIN order_reviews r ON o.order_id = r.order_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
  AND o.order_estimated_delivery_date IS NOT NULL;
"""


@router.get("/delay-vs-review")
@cached(prefix="delay_vs_review")
async def get_delay_vs_review(db: Session = Depends(get_db)):
    """Buckets orders by delivery delay and shows avg review score per
    bucket, plus the Pearson correlation coefficient between delay
    days and review score."""
    try:
        buckets = run_query(db, DELAY_BUCKET_SQL)
        correlation = run_query(db, CORRELATION_SQL)
        return {
            "buckets": buckets,
            "correlation": correlation[0]["delay_review_correlation"] if correlation else None,
        }
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
