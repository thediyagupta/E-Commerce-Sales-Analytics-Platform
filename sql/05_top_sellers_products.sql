-- ============================================================
-- TOP SELLERS / PRODUCTS BY REGION: uses RANK()/DENSE_RANK() to
-- get top-N per group (per state) in a single query instead of
-- N separate queries -- the classic "greatest-n-per-group" pattern.
-- ============================================================

-- Top 3 sellers by revenue, per seller state
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
    SELECT
        *,
        RANK() OVER (PARTITION BY seller_state ORDER BY total_revenue DESC) AS state_rank
    FROM seller_revenue
)
SELECT seller_state, seller_id, total_revenue, num_orders, state_rank
FROM ranked_sellers
WHERE state_rank <= 3
ORDER BY seller_state, state_rank;


-- Top 3 product categories by revenue, per customer state (i.e. what
-- do customers in each region buy most)
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
    SELECT
        *,
        DENSE_RANK() OVER (PARTITION BY customer_state ORDER BY total_revenue DESC) AS state_rank
    FROM category_revenue
)
SELECT customer_state, category, total_revenue, state_rank
FROM ranked_categories
WHERE state_rank <= 3
ORDER BY customer_state, state_rank;
