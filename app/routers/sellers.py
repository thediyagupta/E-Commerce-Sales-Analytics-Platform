from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.database import get_db, run_query
from app.cache import cached

router = APIRouter(prefix="/api/v1", tags=["sellers"])

TOP_SELLERS_SQL = """
WITH seller_revenue AS (
    SELECT
        s.seller_state,
        s.seller_id,
        SUM(oi.price) AS total_revenue,
        COUNT(DISTINCT oi.order_id) AS num_orders
    FROM order_items oi
    JOIN sellers s ON oi.seller_id = s.seller_id
    JOIN orders o ON oi.order_id = o.order_id
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY s.seller_state, s.seller_id
),
ranked_sellers AS (
    SELECT *, RANK() OVER (PARTITION BY seller_state ORDER BY total_revenue DESC) AS state_rank
    FROM seller_revenue
)
SELECT seller_state, seller_id, total_revenue, num_orders, state_rank
FROM ranked_sellers
WHERE state_rank <= :top_n
ORDER BY seller_state, state_rank;
"""

TOP_CATEGORIES_SQL = """
WITH category_revenue AS (
    SELECT
        c.customer_state,
        pt.product_category_name_english AS category,
        SUM(oi.price) AS total_revenue
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    JOIN customers c ON o.customer_id = c.customer_id
    JOIN products p ON oi.product_id = p.product_id
    JOIN product_category_translation pt ON p.product_category_name = pt.product_category_name
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY c.customer_state, pt.product_category_name_english
),
ranked_categories AS (
    SELECT *, DENSE_RANK() OVER (PARTITION BY customer_state ORDER BY total_revenue DESC) AS state_rank
    FROM category_revenue
)
SELECT customer_state, category, total_revenue, state_rank
FROM ranked_categories
WHERE state_rank <= :top_n
ORDER BY customer_state, state_rank;
"""


@router.get("/sellers/top-by-region")
@cached(prefix="top_sellers_by_region")
async def get_top_sellers_by_region(
    top_n: int = Query(3, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """Top-N sellers by revenue within each seller state (RANK())."""
    try:
        rows = run_query(db, TOP_SELLERS_SQL, {"top_n": top_n})
        return {"data": rows, "count": len(rows)}
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.get("/products/top-categories-by-region")
@cached(prefix="top_categories_by_region")
async def get_top_categories_by_region(
    top_n: int = Query(3, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """Top-N product categories by revenue within each customer state (DENSE_RANK())."""
    try:
        rows = run_query(db, TOP_CATEGORIES_SQL, {"top_n": top_n})
        return {"data": rows, "count": len(rows)}
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
