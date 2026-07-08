-- ============================================================
-- RFM SEGMENTATION: Recency, Frequency, Monetary scoring using
-- NTILE(4) to bucket customers into quartiles on each dimension,
-- then combine into a segment label.
-- ============================================================

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
        -- Recency: days since last order, relative to the most recent
        -- date in the whole dataset (since we have no "today")
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
        -- NTILE(4): quartile 1 = best. Recency is inverted (lower days = better = higher score)
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
    r_score,
    f_score,
    m_score,
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
ORDER BY rfm_total ASC;

-- Note: because ~97% of Olist customers order exactly once, frequency
-- quartiles will be heavily skewed (most people tie at frequency=1).
-- Worth mentioning explicitly: NTILE still splits ties arbitrarily
-- into buckets, so f_score here is a much weaker signal than r_score
-- or m_score for this specific dataset -- a real limitation to name
-- in an interview rather than hide.
