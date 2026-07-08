-- ============================================================
-- DELIVERY DELAY vs REVIEW SCORE: does being late correlate with
-- lower ratings? Buckets delay into bands and compares avg review.
-- ============================================================

WITH delivery_facts AS (
    SELECT
        o.order_id,
        r.review_score,
        o.order_estimated_delivery_date,
        o.order_delivered_customer_date,
        -- positive = delivered late, negative = delivered early
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
    -- % of orders in this bucket that got a 1 or 2 star review
    ROUND(100.0 * SUM(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_low_reviews
FROM bucketed
GROUP BY delay_bucket
ORDER BY delay_bucket;

-- Correlation coefficient between delay and score (Postgres has this built in)
SELECT
    ROUND(CORR(delay_days, review_score)::NUMERIC, 4) AS delay_review_correlation
FROM delivery_facts;
