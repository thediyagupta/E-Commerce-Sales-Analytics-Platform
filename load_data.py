"""
Loads the 9 Olist CSVs into Postgres in FK-safe order.
Run: python load_data.py
Expects CSVs in ./data/ (download from Kaggle: olistbr/brazilian-ecommerce)
"""
import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()  # reads .env in the current directory into os.environ

DB_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/olist")
print(f"Connecting using: {DB_URL}")
DATA_DIR = "data"
engine = create_engine(DB_URL)

# Parents before children, to satisfy FK constraints
LOAD_ORDER = [
    ("olist_customers_dataset.csv", "customers"),
    ("olist_sellers_dataset.csv", "sellers"),
    ("product_category_name_translation.csv", "product_category_translation"),
    ("olist_products_dataset.csv", "products"),
    ("olist_orders_dataset.csv", "orders"),
    ("olist_order_items_dataset.csv", "order_items"),
    ("olist_order_payments_dataset.csv", "order_payments"),
    ("olist_order_reviews_dataset.csv", "order_reviews"),
    ("olist_geolocation_dataset.csv", "geolocation"),
]

TIMESTAMP_COLS = {
    "orders": ["order_purchase_timestamp", "order_approved_at",
               "order_delivered_carrier_date", "order_delivered_customer_date",
               "order_estimated_delivery_date"],
    "order_items": ["shipping_limit_date"],
    "order_reviews": ["review_creation_date", "review_answer_timestamp"],
}


def get_schema_columns(table: str):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name = :t"),
            {"t": table},
        )
        return [r[0] for r in result.fetchall()]


def load_csv(filename: str, table: str):
    path = os.path.join(DATA_DIR, filename)
    df = pd.read_csv(path)

    schema_cols = get_schema_columns(table)
    # products.csv has extra columns (name length, description length, photos qty)
    # that we intentionally left out of the schema -- keep only what we modeled
    df = df[[c for c in df.columns if c in schema_cols]]

    for col in TIMESTAMP_COLS.get(table, []):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # products/orders can have some duplicate rows in raw CSV -- drop exact dupes
    df = df.drop_duplicates()

    df.to_sql(table, engine, if_exists="append", index=False, method="multi", chunksize=5000)
    print(f"[OK] {table}: loaded {len(df)} rows")


def run_sanity_checks():
    checks = {
        "orphan order_items (missing product)": """
            SELECT COUNT(*) FROM order_items oi
            LEFT JOIN products p ON oi.product_id = p.product_id
            WHERE p.product_id IS NULL
        """,
        "orphan order_items (missing seller)": """
            SELECT COUNT(*) FROM order_items oi
            LEFT JOIN sellers s ON oi.seller_id = s.seller_id
            WHERE s.seller_id IS NULL
        """,
        "orders with no order_items": """
            SELECT COUNT(*) FROM orders o
            LEFT JOIN order_items oi ON o.order_id = oi.order_id
            WHERE oi.order_id IS NULL
        """,
        "products with no category": """
            SELECT COUNT(*) FROM products WHERE product_category_name IS NULL
        """,
    }
    print("\n--- Data quality sanity checks ---")
    with engine.connect() as conn:
        for label, sql in checks.items():
            count = conn.execute(text(sql)).scalar()
            print(f"{label}: {count}")


if __name__ == "__main__":
    for filename, table in LOAD_ORDER:
        try:
            load_csv(filename, table)
        except Exception as e:
            print(f"[FAILED] {table}: {e}")
    run_sanity_checks()
