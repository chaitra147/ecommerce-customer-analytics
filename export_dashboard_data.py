"""
Re-exports the flattened, dashboard-ready CSV from ecommerce.db.
Run this any time the underlying data changes (e.g. after swapping in
real Olist data) so Power BI / Tableau have the latest numbers.
"""

import sqlite3
import pandas as pd
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE, "ecommerce.db")
OUT_PATH = os.path.join(BASE, "dashboard", "dashboard_dataset.csv")

conn = sqlite3.connect(DB_PATH)

query = """
SELECT
    o.order_id, o.customer_id, c.customer_name, c.customer_state, c.customer_city,
    o.order_purchase_ts, o.order_status, o.delivery_days,
    oi.product_id, p.product_category, oi.quantity, oi.unit_price, oi.freight_value,
    (oi.unit_price*oi.quantity + oi.freight_value) AS line_total,
    r.review_score
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
LEFT JOIN order_reviews r ON o.order_id = r.order_id
WHERE o.order_status = 'delivered'
"""

df = pd.read_sql_query(query, conn)
df.to_csv(OUT_PATH, index=False)
print(f"Exported {len(df):,} rows, {df.shape[1]} columns to:")
print(OUT_PATH)
