from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.database import get_db, run_query
from app.cache import cached

router = APIRouter(prefix="/api/v1/revenue", tags=["revenue"])

REVENUE_TRENDS_SQL = """
WITH monthly_revenue AS (
    SELECT
        DATE_TRUNC('month', o.order_purchase_timestamp)::DATE AS month,
        SUM(oi.price + oi.freight_value) AS total_revenue,
        COUNT(DISTINCT o.order_id) AS order_count
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY 1
)
SELECT
    month,
    total_revenue,
    order_count,
    ROUND(total_revenue / NULLIF(order_count, 0), 2) AS avg_order_value,
    LAG(total_revenue) OVER (ORDER BY month) AS prev_month_revenue,
    ROUND(
        100.0 * (total_revenue - LAG(total_revenue) OVER (ORDER BY month))
        / NULLIF(LAG(total_revenue) OVER (ORDER BY month), 0), 2
    ) AS mom_growth_pct,
    ROUND(
        AVG(total_revenue) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2
    ) AS rolling_3mo_avg_revenue
FROM monthly_revenue
ORDER BY month;
"""


@router.get("/trends")
@cached(prefix="revenue_trends")
async def get_revenue_trends(db: Session = Depends(get_db)):
    """Monthly revenue with MoM growth (LAG) and 3-month rolling average.
    Cached because this scans the full orders+order_items join."""
    try:
        rows = run_query(db, REVENUE_TRENDS_SQL)
        return {"data": rows, "count": len(rows)}
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
