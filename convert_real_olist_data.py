"""
Converts the REAL Olist Kaggle dataset into the same CSV schema this project
already uses, so every downstream script (load_data.py, analysis.py, the
Excel workbook builder, the dashboard export) works with ZERO code changes.

BEFORE RUNNING:
1. Download & extract the dataset from:
   https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
2. Set RAW_DIR below to the folder where you extracted the 9 CSV files.

Run this from the project's `data` folder:
    python convert_real_olist_data.py
It will overwrite customers.csv, products.csv, orders.csv, order_items.csv,
order_payments.csv, order_reviews.csv with the REAL data, in the same format
your project already expects.
"""

import pandas as pd
import os

# ---- EDIT THIS to wherever you extracted the Kaggle zip ----
RAW_DIR = r"C:\Users\cchai\Downloads\archive"
# --------------------------------------------------------------

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

def load(name):
    path = os.path.join(RAW_DIR, name)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Could not find {name} in {RAW_DIR}\n"
            f"Check that RAW_DIR points to the folder with the extracted Kaggle CSVs."
        )
    return pd.read_csv(path)

print("Loading real Olist files...")
raw_customers = load("olist_customers_dataset.csv")
raw_orders    = load("olist_orders_dataset.csv")
raw_items     = load("olist_order_items_dataset.csv")
raw_payments  = load("olist_order_payments_dataset.csv")
raw_reviews   = load("olist_order_reviews_dataset.csv")
raw_products  = load("olist_products_dataset.csv")
try:
    cat_translation = load("product_category_name_translation.csv")
except FileNotFoundError:
    cat_translation = None

# ---------------------------------------------------------------
# 1. CUSTOMERS
#    Real data has customer_unique_id (the true person) AND customer_id
#    (unique per ORDER). We use customer_unique_id as our customer_id so
#    repeat purchases actually link to the same customer -- this matters
#    a lot for RFM/cohort analysis to work correctly.
# ---------------------------------------------------------------
customers = raw_customers[["customer_unique_id", "customer_city", "customer_state"]].rename(
    columns={"customer_unique_id": "customer_id"}
).drop_duplicates(subset="customer_id")
customers["customer_name"] = "Customer_" + customers["customer_id"].astype(str).str[:8]  # real data has no names (anonymized)
customers["signup_date"] = pd.NaT  # real data has no signup date
customers = customers[["customer_id", "customer_name", "customer_state", "customer_city", "signup_date"]]

# Map from the per-order customer_id (in raw_orders) to our real customer_id
id_map = raw_customers.set_index("customer_id")["customer_unique_id"]

# ---------------------------------------------------------------
# 2. PRODUCTS
# ---------------------------------------------------------------
products = raw_products.rename(columns={
    "product_weight_g": "weight_g",
})[["product_id", "product_category_name", "weight_g"]]

if cat_translation is not None:
    products = products.merge(cat_translation, on="product_category_name", how="left")
    products["product_category"] = products["product_category_name_english"].fillna(products["product_category_name"])
else:
    products["product_category"] = products["product_category_name"]

# Real data has no product-level price -- price lives on order_items, so
# we compute an average price per product from order_items below and merge it in.

products = products[["product_id", "product_category", "weight_g"]]

# ---------------------------------------------------------------
# 3. ORDERS
# ---------------------------------------------------------------
orders = raw_orders.copy()
orders["customer_id"] = orders["customer_id"].map(id_map)  # translate to real customer_id
orders["delivery_days"] = (
    pd.to_datetime(orders["order_delivered_customer_date"]) -
    pd.to_datetime(orders["order_purchase_timestamp"])
).dt.days

orders = orders.rename(columns={
    "order_purchase_timestamp": "order_purchase_ts",
    "order_delivered_customer_date": "delivered_ts",
    "order_status": "order_status",
})[["order_id", "customer_id", "order_purchase_ts", "order_status", "delivered_ts", "delivery_days"]]

# ---------------------------------------------------------------
# 4. ORDER ITEMS
# ---------------------------------------------------------------
order_items = raw_items.rename(columns={
    "price": "unit_price",
})
order_items["order_item_id"] = range(1, len(order_items) + 1)
order_items["quantity"] = 1  # Olist order_items has one row per unit already
order_items = order_items[["order_item_id", "order_id", "product_id", "quantity", "unit_price", "freight_value"]]

# now backfill an average price onto products (nice-to-have, used nowhere critical)
avg_price = order_items.groupby("product_id")["unit_price"].mean().rename("price")
products = products.merge(avg_price, on="product_id", how="left")
products["price"] = products["price"].fillna(products["price"].median())
products = products[["product_id", "product_category", "price", "weight_g"]]

# ---------------------------------------------------------------
# 5. PAYMENTS
#    Real data can have multiple payment rows per order (split payments) --
#    we collapse to one row per order to match our schema.
# ---------------------------------------------------------------
payments = raw_payments.groupby("order_id").agg(
    payment_type=("payment_type", "first"),
    installments=("payment_installments", "max"),
    payment_value=("payment_value", "sum"),
).reset_index()

# ---------------------------------------------------------------
# 6. REVIEWS
# ---------------------------------------------------------------
reviews = raw_reviews.rename(columns={
    "review_creation_date": "review_ts",
})[["order_id", "review_score", "review_ts"]]
# keep one review per order (real data occasionally has duplicates)
reviews = reviews.drop_duplicates(subset="order_id")

# ---------------------------------------------------------------
# SAVE — overwrites your existing synthetic CSVs with real data
# ---------------------------------------------------------------
customers.to_csv(os.path.join(OUT_DIR, "customers.csv"), index=False)
products.to_csv(os.path.join(OUT_DIR, "products.csv"), index=False)
orders.to_csv(os.path.join(OUT_DIR, "orders.csv"), index=False)
order_items.to_csv(os.path.join(OUT_DIR, "order_items.csv"), index=False)
payments.to_csv(os.path.join(OUT_DIR, "order_payments.csv"), index=False)
reviews.to_csv(os.path.join(OUT_DIR, "order_reviews.csv"), index=False)

print("\nReal Olist data converted successfully:")
print(f"  customers.csv       {len(customers):,} rows")
print(f"  products.csv        {len(products):,} rows")
print(f"  orders.csv          {len(orders):,} rows")
print(f"  order_items.csv     {len(order_items):,} rows")
print(f"  order_payments.csv  {len(payments):,} rows")
print(f"  order_reviews.csv   {len(reviews):,} rows")
print("\nNext: run  python sql\\load_data.py  then  python notebooks\\analysis.py")
