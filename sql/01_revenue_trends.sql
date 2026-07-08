-- ============================================================
-- REVENUE TRENDS: monthly revenue, MoM growth, 3-month rolling average
-- Concepts used: LAG (previous row), window frame (ROWS BETWEEN) for
-- moving average, all partitioned/ordered without collapsing rows via GROUP BY.
-- ============================================================

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

    -- LAG: previous month's revenue, to compute MoM growth
    LAG(total_revenue) OVER (ORDER BY month) AS prev_month_revenue,
    ROUND(
        100.0 * (total_revenue - LAG(total_revenue) OVER (ORDER BY month))
        / NULLIF(LAG(total_revenue) OVER (ORDER BY month), 0),
        2
    ) AS mom_growth_pct,

    -- 3-month rolling average revenue (trailing window frame)
    ROUND(
        AVG(total_revenue) OVER (
            ORDER BY month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ), 2
    ) AS rolling_3mo_avg_revenue

FROM monthly_revenue
ORDER BY month;


-- ============================================================
-- Bonus: YoY comparison using LAG with an offset that matches same
-- calendar month a year prior (useful if dataset spans >12 months)
-- ============================================================
WITH monthly_revenue AS (
    SELECT
        DATE_TRUNC('month', o.order_purchase_timestamp)::DATE AS month,
        SUM(oi.price + oi.freight_value) AS total_revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY 1
)
SELECT
    month,
    total_revenue,
    LAG(total_revenue, 12) OVER (ORDER BY month) AS revenue_12mo_ago,
    ROUND(
        100.0 * (total_revenue - LAG(total_revenue, 12) OVER (ORDER BY month))
        / NULLIF(LAG(total_revenue, 12) OVER (ORDER BY month), 0),
        2
    ) AS yoy_growth_pct
FROM monthly_revenue
ORDER BY month;
