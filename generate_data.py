"""
Generates a synthetic e-commerce dataset structured exactly like the real
Olist Brazilian E-Commerce dataset (Kaggle), so you can build/run this whole
project now, then swap in the real CSVs later without changing any code.

Tables generated:
    customers, orders, order_items, products, order_payments, order_reviews

Intentional data quality issues are injected (nulls, duplicates, outliers)
so the cleaning step in the project is realistic, not trivial.
"""

import numpy as np
import pandas as pd
import random
from datetime import datetime, timedelta

np.random.seed(42)
random.seed(42)

N_CUSTOMERS = 3000
N_ORDERS = 8000
STATES = ["SP", "RJ", "MG", "RS", "PR", "SC", "BA", "DF", "GO", "PE"]
STATE_WEIGHTS = [0.32, 0.13, 0.12, 0.09, 0.08, 0.06, 0.06, 0.05, 0.05, 0.04]

CATEGORIES = [
    "electronics", "home_decor", "beauty", "sports_leisure", "fashion_accessories",
    "furniture", "toys", "books", "garden_tools", "computers_accessories",
    "watches_gifts", "housewares", "baby", "auto", "office_supplies"
]

FIRST_NAMES = ["Maria","Jose","Ana","Joao","Antonio","Francisca","Carlos","Paulo",
    "Marcos","Luiz","Juliana","Fernanda","Rafael","Camila","Bruno","Patricia",
    "Rodrigo","Aline","Diego","Vanessa"]
LAST_NAMES = ["Silva","Santos","Oliveira","Souza","Rodrigues","Ferreira","Alves",
    "Pereira","Lima","Gomes","Costa","Ribeiro","Martins","Carvalho","Almeida"]

def rand_date(start, end):
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))

# ---------------------------------------------------------------------------
# 1. CUSTOMERS
# ---------------------------------------------------------------------------
customers = []
for i in range(1, N_CUSTOMERS + 1):
    customers.append({
        "customer_id": f"CUST{i:05d}",
        "customer_name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
        "customer_state": np.random.choice(STATES, p=STATE_WEIGHTS),
        "customer_city": random.choice(["Sao Paulo","Rio de Janeiro","Belo Horizonte",
            "Porto Alegre","Curitiba","Salvador","Brasilia","Recife","Florianopolis","Goiania"]),
        "signup_date": rand_date(datetime(2016,1,1), datetime(2018,6,1)).date(),
    })
customers_df = pd.DataFrame(customers)

# inject a few duplicate customer rows (data quality issue)
dupes = customers_df.sample(15, random_state=1)
customers_df = pd.concat([customers_df, dupes], ignore_index=True)
# inject a few missing cities
customers_df.loc[customers_df.sample(20, random_state=2).index, "customer_city"] = None

# ---------------------------------------------------------------------------
# 2. PRODUCTS
# ---------------------------------------------------------------------------
N_PRODUCTS = 500
products = []
for i in range(1, N_PRODUCTS + 1):
    cat = random.choice(CATEGORIES)
    base_price = {
        "electronics": 450, "computers_accessories": 300, "furniture": 550,
        "watches_gifts": 250, "auto": 200, "office_supplies": 80,
    }.get(cat, 100)
    products.append({
        "product_id": f"PROD{i:04d}",
        "product_category": cat,
        "price": round(max(9.9, np.random.normal(base_price, base_price*0.4)), 2),
        "weight_g": int(np.random.uniform(100, 15000)),
    })
products_df = pd.DataFrame(products)

# ---------------------------------------------------------------------------
# 3. ORDERS  (skewed so repeat customers exist -> makes RFM/cohort meaningful)
# ---------------------------------------------------------------------------
# 60% of orders come from a "core" 25% of customers (repeat buyers)
core_customers = customers_df["customer_id"].sample(frac=0.25, random_state=3).tolist()
all_customers = customers_df["customer_id"].tolist()

orders = []
order_start = datetime(2017, 1, 1)
order_end = datetime(2018, 12, 31)

for i in range(1, N_ORDERS + 1):
    if random.random() < 0.6:
        cust = random.choice(core_customers)
    else:
        cust = random.choice(all_customers)

    order_ts = rand_date(order_start, order_end)
    status = np.random.choice(
        ["delivered", "shipped", "canceled", "delivered", "delivered"],
        p=[0.78, 0.06, 0.05, 0.06, 0.05]
    )
    delivery_days = max(1, int(np.random.normal(9, 4)))
    delivered_ts = order_ts + timedelta(days=delivery_days) if status == "delivered" else None

    orders.append({
        "order_id": f"ORD{i:06d}",
        "customer_id": cust,
        "order_purchase_ts": order_ts,
        "order_status": status,
        "delivered_ts": delivered_ts,
        "delivery_days": delivery_days if status == "delivered" else None,
    })
orders_df = pd.DataFrame(orders)

# inject some null timestamps (bad scrapes / system errors)
orders_df.loc[orders_df.sample(25, random_state=4).index, "order_purchase_ts"] = pd.NaT

# ---------------------------------------------------------------------------
# 4. ORDER ITEMS (each order has 1-4 line items)
# ---------------------------------------------------------------------------
order_items = []
item_id_counter = 1
for _, row in orders_df.iterrows():
    n_items = np.random.choice([1, 2, 3, 4], p=[0.55, 0.25, 0.13, 0.07])
    chosen_products = products_df.sample(n_items, random_state=item_id_counter % 500)
    for _, prod in chosen_products.iterrows():
        qty = np.random.choice([1, 1, 1, 2], p=[0.7, 0.15, 0.1, 0.05])
        order_items.append({
            "order_item_id": item_id_counter,
            "order_id": row["order_id"],
            "product_id": prod["product_id"],
            "quantity": int(qty),
            "unit_price": prod["price"],
            "freight_value": round(np.random.uniform(5, 45), 2),
        })
        item_id_counter += 1
order_items_df = pd.DataFrame(order_items)

# ---------------------------------------------------------------------------
# 5. PAYMENTS
# ---------------------------------------------------------------------------
payment_types = ["credit_card", "boleto", "voucher", "debit_card"]
payments = []
for _, row in orders_df.iterrows():
    order_total = order_items_df.loc[order_items_df.order_id == row.order_id,
                                      ["unit_price", "quantity", "freight_value"]].apply(
        lambda r: r.unit_price * r.quantity + r.freight_value, axis=1).sum()
    installments = np.random.choice([1, 2, 3, 6, 10], p=[0.4, 0.2, 0.15, 0.15, 0.1])
    payments.append({
        "order_id": row["order_id"],
        "payment_type": np.random.choice(payment_types, p=[0.75, 0.18, 0.04, 0.03]),
        "installments": int(installments),
        "payment_value": round(order_total, 2),
    })
payments_df = pd.DataFrame(payments)

# ---------------------------------------------------------------------------
# 6. REVIEWS (correlated with delivery speed -> gives you a real insight to find)
# ---------------------------------------------------------------------------
reviews = []
for _, row in orders_df.iterrows():
    if row["order_status"] != "delivered" or pd.isna(row["delivery_days"]):
        continue
    if row["delivery_days"] <= 7:
        score = np.random.choice([5, 4, 3, 2, 1], p=[0.55, 0.3, 0.1, 0.03, 0.02])
    elif row["delivery_days"] <= 14:
        score = np.random.choice([5, 4, 3, 2, 1], p=[0.25, 0.35, 0.25, 0.1, 0.05])
    else:
        score = np.random.choice([5, 4, 3, 2, 1], p=[0.05, 0.15, 0.25, 0.3, 0.25])
    reviews.append({
        "order_id": row["order_id"],
        "review_score": int(score),
        "review_ts": row["delivered_ts"] + timedelta(days=random.randint(0, 5)),
    })
reviews_df = pd.DataFrame(reviews)

# ---------------------------------------------------------------------------
# SAVE
# ---------------------------------------------------------------------------
import os
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

customers_df.to_csv(os.path.join(OUT_DIR, "customers.csv"), index=False)
products_df.to_csv(os.path.join(OUT_DIR, "products.csv"), index=False)
orders_df.to_csv(os.path.join(OUT_DIR, "orders.csv"), index=False)
order_items_df.to_csv(os.path.join(OUT_DIR, "order_items.csv"), index=False)
payments_df.to_csv(os.path.join(OUT_DIR, "order_payments.csv"), index=False)
reviews_df.to_csv(os.path.join(OUT_DIR, "order_reviews.csv"), index=False)

print("Generated:")
print(f"  customers.csv       {len(customers_df):,} rows")
print(f"  products.csv        {len(products_df):,} rows")
print(f"  orders.csv          {len(orders_df):,} rows")
print(f"  order_items.csv     {len(order_items_df):,} rows")
print(f"  order_payments.csv  {len(payments_df):,} rows")
print(f"  order_reviews.csv   {len(reviews_df):,} rows")
