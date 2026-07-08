-- ============================================================
-- COHORT RETENTION: group customers by the month of their FIRST
-- order (their "cohort"), then measure what % of each cohort placed
-- another order N months later.
--
-- IMPORTANT: uses customer_unique_id, not customer_id -- Olist
-- assigns a fresh customer_id per order, so customer_id would make
-- every customer look like a one-time buyer. This is the single
-- most important modeling decision in this whole analysis.
-- ============================================================

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
    SELECT
        customer_unique_id,
        MIN(order_month) AS cohort_month
    FROM customer_orders
    GROUP BY customer_unique_id
),

cohort_activity AS (
    SELECT
        fp.cohort_month,
        co.order_month,
        -- month_number = how many months after the cohort's first purchase
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
    SELECT
        cohort_month,
        month_number,
        COUNT(DISTINCT customer_unique_id) AS active_customers
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

-- Note for your README/interview: Olist's dataset is dominated by
-- one-time buyers (~97%), so most retention_pct values beyond
-- month_number = 0 will be low/near-zero. That's a real, defensible
-- finding about the marketplace -- state it as an insight, not a bug.
