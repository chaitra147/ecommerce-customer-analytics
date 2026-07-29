"""
Loads the CSVs in /data into a SQLite database (ecommerce.db) using the
schema in 01_create_schema.sql.

Run this once before running any of the .sql query files or the
Python notebooks.
"""

import sqlite3
import pandas as pd
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE, "ecommerce.db")
DATA_DIR = os.path.join(BASE, "data")
SCHEMA_PATH = os.path.join(BASE, "sql", "01_create_schema.sql")

conn = sqlite3.connect(DB_PATH)

# 1. Create schema
with open(SCHEMA_PATH) as f:
    conn.executescript(f.read())

# 2. Load + light-clean each CSV, then insert
tables = {
    "customers": "customers.csv",
    "products": "products.csv",
    "orders": "orders.csv",
    "order_items": "order_items.csv",
    "order_payments": "order_payments.csv",
    "order_reviews": "order_reviews.csv",
}

for table, filename in tables.items():
    df = pd.read_csv(os.path.join(DATA_DIR, filename))

    # --- basic cleaning (this is the "Excel exploration" issues, fixed in code) ---
    if table == "customers":
        before = len(df)
        df = df.drop_duplicates(subset="customer_id")
        print(f"customers: dropped {before - len(df)} duplicate rows")

    df.to_sql(table, conn, if_exists="append", index=False)
    print(f"Loaded {len(df):,} rows into '{table}'")

conn.commit()
conn.close()
print(f"\nDatabase ready at: {DB_PATH}")
