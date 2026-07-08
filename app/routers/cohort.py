from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.database import get_db, run_query
from app.cache import cached

router = APIRouter(prefix="/api/v1/cohort", tags=["cohort"])

COHORT_RETENTION_SQL = """
WITH customer_orders AS (
    SELECT
        c.customer_unique_id,
        o.order_id,
        DATE_TRUNC('month', o.order_purchase_timestamp)::DATE AS order_month
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
),
first_purchase AS (
    SELECT customer_unique_id, MIN(order_month) AS cohort_month
    FROM customer_orders
    GROUP BY customer_unique_id
),
cohort_activity AS (
    SELECT
        fp.cohort_month,
        (EXTRACT(YEAR FROM co.order_month) - EXTRACT(YEAR FROM fp.cohort_month)) * 12
            + (EXTRACT(MONTH FROM co.order_month) - EXTRACT(MONTH FROM fp.cohort_month)) AS month_number,
        co.customer_unique_id
    FROM customer_orders co
    JOIN first_purchase fp ON co.customer_unique_id = fp.customer_unique_id
),
cohort_size AS (
    SELECT cohort_month, COUNT(DISTINCT customer_unique_id) AS num_customers
    FROM first_purchase
    GROUP BY cohort_month
),
retention_table AS (
    SELECT cohort_month, month_number, COUNT(DISTINCT customer_unique_id) AS active_customers
    FROM cohort_activity
    GROUP BY cohort_month, month_number
)
SELECT
    r.cohort_month,
    r.month_number,
    cs.num_customers AS cohort_size,
    r.active_customers,
    ROUND(100.0 * r.active_customers / cs.num_customers, 2) AS retention_pct
FROM retention_table r
JOIN cohort_size cs ON r.cohort_month = cs.cohort_month
ORDER BY r.cohort_month, r.month_number;
"""


@router.get("/retention")
@cached(prefix="cohort_retention")
async def get_cohort_retention(db: Session = Depends(get_db)):
    """Monthly cohort retention matrix. Uses customer_unique_id (not
    customer_id) since Olist mints a new customer_id per order."""
    try:
        rows = run_query(db, COHORT_RETENTION_SQL)
        return {"data": rows, "count": len(rows)}
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
