-- ============================================================
-- Olist E-Commerce Schema
-- Design notes (put these in your README / say them in interviews):
--   1. customer_id vs customer_unique_id: Olist gives each ORDER a
--      new customer_id, but customer_unique_id is the real person.
--      This matters a lot for cohort/RFM analysis -- if you group by
--      customer_id you will undercount repeat customers.
--   2. order_reviews has (review_id, order_id) as composite PK because
--      a tiny number of review_ids repeat across different orders in
--      the raw data.
--   3. Indexes are chosen based on the actual query patterns in sql/,
--      not added blindly -- e.g. we index order_purchase_timestamp
--      because every time-series/cohort query filters or groups on it.
-- ============================================================

CREATE TABLE customers (
    customer_id VARCHAR(32) PRIMARY KEY,
    customer_unique_id VARCHAR(32) NOT NULL,
    customer_zip_code_prefix INT,
    customer_city VARCHAR(100),
    customer_state VARCHAR(2)
);

CREATE TABLE sellers (
    seller_id VARCHAR(32) PRIMARY KEY,
    seller_zip_code_prefix INT,
    seller_city VARCHAR(100),
    seller_state VARCHAR(2)
);

CREATE TABLE product_category_translation (
    product_category_name VARCHAR(100) PRIMARY KEY,
    product_category_name_english VARCHAR(100)
);

CREATE TABLE products (
    product_id VARCHAR(32) PRIMARY KEY,
    product_category_name VARCHAR(100) ,
    product_weight_g INT,
    product_length_cm INT,
    product_height_cm INT,
    product_width_cm INT
);

CREATE TABLE orders (
    order_id VARCHAR(32) PRIMARY KEY,
    customer_id VARCHAR(32) REFERENCES customers(customer_id),
    order_status VARCHAR(20),
    order_purchase_timestamp TIMESTAMP,
    order_approved_at TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP
);

CREATE TABLE order_items (
    order_id VARCHAR(32) REFERENCES orders(order_id),
    order_item_id INT,
    product_id VARCHAR(32) REFERENCES products(product_id),
    seller_id VARCHAR(32) REFERENCES sellers(seller_id),
    shipping_limit_date TIMESTAMP,
    price NUMERIC(10,2),
    freight_value NUMERIC(10,2),
    PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE order_payments (
    order_id VARCHAR(32) REFERENCES orders(order_id),
    payment_sequential INT,
    payment_type VARCHAR(20),
    payment_installments INT,
    payment_value NUMERIC(10,2),
    PRIMARY KEY (order_id, payment_sequential)
);

CREATE TABLE order_reviews (
    review_id VARCHAR(32),
    order_id VARCHAR(32) REFERENCES orders(order_id),
    review_score INT,
    review_comment_title TEXT,
    review_comment_message TEXT,
    review_creation_date TIMESTAMP,
    review_answer_timestamp TIMESTAMP,
    PRIMARY KEY (review_id, order_id)
);

CREATE TABLE geolocation (
    geolocation_zip_code_prefix INT,
    geolocation_lat NUMERIC(10,6),
    geolocation_lng NUMERIC(10,6),
    geolocation_city VARCHAR(100),
    geolocation_state VARCHAR(2)
);

-- ---------- Indexes (added for the query patterns in sql/*.sql) ----------
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_purchase_ts ON orders(order_purchase_timestamp);
CREATE INDEX idx_orders_status ON orders(order_status);
CREATE INDEX idx_order_items_product ON order_items(product_id);
CREATE INDEX idx_order_items_seller ON order_items(seller_id);
CREATE INDEX idx_reviews_order ON order_reviews(order_id);
CREATE INDEX idx_payments_order ON order_payments(order_id);
CREATE INDEX idx_customers_unique ON customers(customer_unique_id);
CREATE INDEX idx_sellers_state ON sellers(seller_state);
CREATE INDEX idx_customers_state ON customers(customer_state);
